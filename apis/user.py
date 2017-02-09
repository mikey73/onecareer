import sys
import urllib
import urlparse
import datetime
from common import errors
from common.compat import json

import models as db
from basehandlers import required_auth
from basehandlers import APIHandler, JSONHandler, AuthRequiredHandler
from tools.validate import *
from tools.auth import AuthorizationProvider


class NonAuthHandler(JSONHandler):
    """ NonAuthHandler, all actions did not required api """
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["account/reset/hash/?$", "reset_hash", ("POST",)],
        ["ping/?$", "ping", ("GET", "POST")],
    )

    @Validation({
        Required("vhash"): All(unicode, Strip,),
        Optional("client_id"): All(unicode, Strip),
        Optional("client_secret"): All(unicode, Strip),
    })
    def reset_hash(self):    # validate reset hash
        # todo: fix resource server validate_reset_hash to post with client_id, client_secret
        verify = db.Verification.verify_hash(vhash=self.form.vhash,
                                             expiry=datetime.timedelta(weeks=1),
                                             set_used=False)
        if verify is None:
            raise errors.InvalidVerification

        # do not set invalid or delete verify here,
        # because this vhash will be checked again in password reset
        self.write_resp()



class AuthHandler(APIHandler):
    """ Auth handler, all actions are api required """
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["oauth2/auth/?$", "oauth2_auth", ("POST", )],
        ["oauth2/token/?$", "oauth2_token", ("POST", )],
        ["oauth2/refresh/?$", "oauth2_refresh", ("POST", )],
        ["oauth2/invalidate/?$", "oauth2_invalidate", ("POST", )],
    )

    # actions
    @Validation({
        Required("email"): All(unicode, Strip, Email, Lower,),
        Required("password"): All(unicode, Strip, Length(6, 64)),
    })
    def oauth2_auth(self):
        account = db.Account.get_one(email=self.form.email, api_pk=self.api.pk)
        if not account:
            raise errors.EmailOrPasswordNotFoundError
        if not account.check_password(self.form.password):
            raise errors.EmailOrPasswordNotFoundError
        if not account.is_active:
            raise errors.AccountInactive
        if not account.is_valid:
            raise errors.AccountNotVerified

        self.conn.cache.user_flags.delete(account.pk)

        auth_provider = AuthorizationProvider(self.conn)
        auth_provider.discard_client_user_tokens(account.api.client_id, account.pk)
        auth_provider.set_user_logged(logged_in=True, acc_id=account.pk)

        url_params = {
            "response_type": "code",
            "redirect_uri": "/",
            "client_id": account.api.client_id,
        }
        parts = list(urlparse.urlsplit(self.request.uri))
        parts[3] = urllib.urlencode(url_params)
        encoded = urlparse.urlunsplit(parts)
        api_resp = auth_provider.get_authorization_code_from_uri(encoded)
        location = api_resp.headers.get("Location")
        data = {}
        if location is not None:
            data = urlparse.parse_qs(urlparse.urlparse(location).query)

        if api_resp.status_code != 302 or "error" in data:
            raise errors.AuthError(", ".join(data["error"]))

        self.write_resp(data)

    @Validation({
        Required("code"): All(unicode, Strip),
        Optional("grant_type", default="authorization_code"): All(unicode, Strip),
    })
    def oauth2_token(self):
        auth_provider = AuthorizationProvider(self.conn)
        post_data = {
            "client_id": self.api.client_id,
            "client_secret": self.api.client_secret,
        }
        post_data.update(self.form)
        api_resp = auth_provider.get_token_from_post_data(post_data)
        data = json.loads(api_resp.text) if api_resp.text else dict()
        error = data.get("error")
        if error is not None:
            raise errors.AuthError(str(error))

        self.write_resp(data)

    @Validation({
        Required("access_token"): All(unicode, Strip),
        Required("refresh_token"): All(unicode, Strip),
        Optional("scope", default=""): All(unicode, Strip),
    })
    def oauth2_refresh(self):
        auth_provider = AuthorizationProvider(self.conn)
        form = self.form
        data = auth_provider.from_refresh_token(client_id=self.api.client_id,
                                                refresh_token=form.refresh_token,
                                                scope=form.scope)
        if data is None:
            raise errors.InvalidRefreshToken

        valid = auth_provider.validate_access_token(client_id=self.api.client_id,
                                                    acc_id=data["acc_id"],
                                                    acc_tok=form.access_token)
        if valid is False:
            raise errors.InvalidAccessToken

        result = auth_provider.persist_token_information(client_id=self.api.client_id,
                                                         refresh_token=form.refresh_token,
                                                         scope=form.scope,
                                                         access_token=form.access_token,
                                                         token_type="Bearer",
                                                         expires_in="3600",
                                                         data=data,
                                                         )
        if result is None:
            raise errors.InvalidAuthCredentials

        self.write_resp(result)

    @required_auth
    @Validation({})
    def oauth2_invalidate(self):
        auth_provider = AuthorizationProvider(self.conn)
        auth_provider.discard_client_user_tokens(self.api.client_id, self.auth.acc_id)

        self.conn.cache.user_flags.delete(self.auth.acc_id)

        self.write_resp()


def send_user_email(handler, sender, recipients, subject, site, msg=None,
                    action="", host="", path="", vhash=""):
    # noinspection PyBroadException
    try:
        site_settings = handler.config.site_settings[site]
        if msg is None:
            msg = handler.render_string("email/user.html", site_settings=site_settings,
                                        action=action, host=host, path=path, vhash=vhash)

        if not isinstance(recipients, (tuple, list)):
            recipients = [recipients]
        handler.bg_tasks.send_mail(msg=msg, to_addrs=recipients, sender=sender, subject=subject)
    except:
        handler.log_exception(*sys.exc_info())
        raise
    return


class AccountHandler(APIHandler):
    """ Account handler, some actions are auth required """
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["account/register/?$", "register", ("POST",)],
        ["account/login/?$", "login", ("POST",)],
        ["account/validate/?$", "validate", ("POST",)],
        ["account/recover/?$", "recover", ("POST",)],
        ["account/register/resend/?$", "register_resend", ("POST",)],
        ["account/reset/?$", "reset", ("POST",)],
        ["account/password/reset/?$", "password_reset", ("POST",)],  # deprecated
        ["newsletter_signup/?$", "newsletter_signup", ("POST",)],
    )

    # actions
    @Validation({
        Required("name"): All(unicode, Strip),
        Required("email"): All(unicode, Strip, Email, Lower,),
    })
    def newsletter_signup(self):
        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["webmaster"]
        email = self.config.site_settings[self.api.site]["email"]["contact"]
        send_user_email(self, sender=sender, recipients=email, 
                        msg="%s at %s is interested in the %s newsletter!" % (
                            self.form.name, self.form.email, company
                        ),
                        subject="%s Newsletter Signup" % company)
        self.write_resp()

    @Validation({
        Required("email"): All(unicode, Strip, Email, Lower,),
        Required("password"): All(unicode, Strip, Length(6, 64)),
    })
    def login(self):
        account = db.Account.get_one(email=self.form.email, api_pk=self.api.pk)
        if not account:
            raise errors.EmailOrPasswordNotFoundError
        if not account.check_password(self.form.password):
            raise errors.EmailOrPasswordNotFoundError
        if not account.is_active:
            raise errors.AccountInactive
        if not account.is_valid:
            raise errors.AccountNotVerified

        self.conn.cache.user_flags.delete(account.pk)

        auth_provider = AuthorizationProvider(self.conn)
        auth_provider.discard_client_user_tokens(account.api.client_id, account.pk)
        auth_provider.set_user_logged(logged_in=True, acc_id=account.pk)

        self.write_resp(account.to_dict())

    @Validation({
        Required("email"): All(unicode, Strip, Email, Lower,),
        Required("password"): All(unicode, Strip, Length(6, 64)),
        Required("fullname"): All(unicode, Strip, Length(2, 64)),
        Required("role"): All(unicode, Strip),
    })
    def register(self):
        fullname = self.form.fullname
        email = self.form.email
        password = self.form.password
        role = self.form.role

        if role not in db.AccountRoles.values():
            raise errors.InvalidRoleError

        if db.Account.check_exist(email=email, api_pk=self.api.id):
            raise errors.EmailExistsError

        user = db.Account.new(fullname=fullname,
                              email=email,
                              password=password,
                              role=role,
                              api_pk=self.api.id)

        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["registration"]

        self.write_resp()

        send_user_email(self, sender=sender, recipients=user.email, site=self.api.site,
                            vhash=user.verify.vhash, action="validate",
                            path=self.config.action_path["validate"], host=self.config.site_settings[self.api.site]["host"],
                            subject="%s Account Registration Confirmation" % company)


    @Validation({
        Required("vhash"): All(unicode, Strip),
    })
    def validate(self):
        verify = db.Verification.verify_hash(vhash=self.form.vhash,
                                             expiry=datetime.timedelta(weeks=1))
        if verify is None:
            raise errors.InvalidVerification

        verify.account.is_valid = True
        verify.account.save()

        self.write_resp()

    @Validation({
        Required("email"): All(unicode, Strip, Email, Lower,),
    })
    def register_resend(self):
        # noinspection PyUnusedLocal
        verify = db.Account.renew_verification(email=self.form.email, api_pk=self.api.id)

        if self.config.debug:
            # warning: send out verify vhash for test purpose only
            self.write_resp(verify.to_dict())
        else:
            self.write_resp()

        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["registration"]
        send_user_email(self, sender=sender, recipients=self.form.email, site=self.api.site,
                        vhash=verify.vhash, action="validate",
                        path=self.config.action_path["validate"], host=self.config.site_settings[self.api.site]["host"],
                        subject="%s Account Registration Confirmation" % company)

    @Validation({
        Required("email"): All(unicode, Strip, Email, Lower,),
    })
    def recover(self):
        # noinspection PyUnusedLocal
        verify = db.Account.renew_verification(email=self.form.email, api_pk=self.api.id)
        if self.config.debug:
            # warning: send out verify vhash for test purpose only
            self.write_resp(verify.to_dict())
        else:
            self.write_resp()

        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["password_reset"]
        send_user_email(self, sender=sender, recipients=self.form.email, site=self.api.site,
                        vhash=verify.vhash, action="reset the password to",
                        path=self.config.action_path["reset"], host=self.config.site_settings[self.api.site]["host"],
                        subject="%s Account Password Reset Request" % company)

    @Validation({
        Required("vhash"): All(unicode, Strip,),
        Required("password"): All(unicode, Strip, Length(6, 64)),
        Required("confirm"): All(unicode, Strip, Length(6, 64)),
    })
    def reset(self):
        if self.form.password != self.form.confirm:
            raise errors.PasswordConfirmError

        verify = db.Verification.verify_hash(vhash=self.form.vhash,
                                             expiry=datetime.timedelta(weeks=1),
                                             set_used=True)
        if verify is None:
            raise errors.InvalidVerification

        account = verify.account

        account.is_valid = True
        account.set_password(password=self.form.password)
        account.save()
        self.write_resp()

        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["password_reset"]
        send_user_email(self, sender=sender, recipients=verify.account.email, site=self.api.site,
                        msg="You've successfully changed your password.",
                        subject="%s Account Password Reset Success" % company)

    # deprecated
    @required_auth
    @Validation({
        Required("password"): All(unicode, Strip, Length(6, 64)),
        Required("confirm"): All(unicode, Strip, Length(6, 64)),
    })
    def password_reset(self):
        if self.form.password != self.form.confirm:
            raise errors.PasswordConfirmError

        account = db.Account.get_and_check(pk=self.auth.acc_id)
        account.set_password(password=self.form.password)
        account.save()
        self.write_resp()

        company = self.config.site_settings[self.api.site]["company"]
        sender = self.config.site_settings[self.api.site]["email"]["password_reset"]
        send_user_email(self, sender=sender, recipients=account.email, site=self.api.site,
                        msg="You've successfully changed your password.",
                        subject="%s Account Password Reset Success" % company)


class AccountInfoHandler(AuthRequiredHandler):
    """ SettingsHandler, all actions are auth required """
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["account/update/?$", "update", ("POST",)],
    )

    @Validation({
        Optional("fullname"): All(unicode, Strip),
        Optional("phone"): All(unicode, Strip),
        Optional("role"): All(unicode, Strip),
        Optional("industry"): All(unicode, Strip),
    })
    def update(self):
        if not self.form:
            self.write_resp()
            return

        account = self.get_cur_account()
        account.update_settings(**self.form)
        account.save(commit=True)

        self.conn.cache.user_flags.delete(account.pk)

        settings = account.get_settings()

        self.write_resp(settings)
