import sys
from basehandlers import BaseHandler
import tornado.web
import datetime
from common import errors
import models as db
import json


def send_user_email(handler, sender, recipients, subject, msg=None,
                    action="", host="", path="", vhash=""):
    # noinspection PyBroadException
    try:
        site_settings = handler.config.site_settings
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


class WelcomeHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('welcome.html', account_info=self.current_user)


class LinkedinLoginHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.render('welcome.html', account_info=self.current_user)
            return

        l_api = self.conn.linkedin_client
        authorization_url = l_api.request_authorization_url(self.config["linkedin_auth"]["redirect_url"])
        self.redirect(authorization_url)


class LinkedinAuthHandler(BaseHandler):
    def get(self):
        code = self.get_argument('code','')
        l_api = self.conn.linkedin_client
        access_token = l_api.request_access_token(self.config["linkedin_auth"]["redirect_url"], code)
        query_params = {'access_token': access_token,
                        'uri': self.config["linkedin_auth"]["uri"],
                        'method': 'GET',
                        'json_post_body': {},
                        'api_type': 'api_people'
                        }
        data = json.loads(l_api.request_api(query_params))
        fullname = data.get("formattedName","")
        email = data.get("emailAddress","")
        password = ""
        role = db.AccountRoles.TBD
        signup_source = db.AccountSignupSource.Linkedin
        if not db.Account.check_exist(email=email, signup_source=signup_source):
            user = db.Account.new(fullname=fullname,
                                  email=email,
                                  password=password,
                                  role=role,
                                  signup_source=signup_source)
        self.session["user_info"] = email
        self.session.save()
        self.set_secure_cookie("incorrect", "0")
        self.render("welcome.html", account_info=self.current_user)


class SignupHandler(BaseHandler):
    def get(self):
        self.render('signup.html', info="")

    def post(self):
        fullname = self.get_argument("fullname")
        email = self.get_argument("email")
        password = self.get_argument("password")
        role = self.get_argument("role")

        try:
            if role not in db.AccountRoles.values():
                raise errors.InvalidRoleError

            if db.Account.check_exist(email=email, signup_source=db.AccountSignupSource.Site):
                raise errors.EmailExistsError
        except Exception, e:
            self.render("signup.html", info=str(e))

        user = db.Account.new(fullname=fullname,
                              email=email,
                              password=password,
                              role=role)

        company = self.config.site_settings["company"]
        sender = self.config.site_settings["email"]["registration"]

        send_user_email(self, sender=sender, recipients=user.email, vhash=user.verify.vhash,
                        action="validate", path=self.config.action_path["validate"],
                        host=self.config.site_settings["host"],
                        subject="%s Account Registration Confirmation" % company)

        self.render('signup.html', info="Registration Success. Please check your email to validate.")


class VerifyHandler(BaseHandler):
    def get(self, vhash):
        try:
            verify = db.Verification.verify_hash(vhash=vhash, expiry=datetime.timedelta(weeks=1))
        except errors.AccountError,e:
            self.render('verify.html', info=str(e))
            return

        verify.account.is_valid = True
        verify.account.save()

        self.render('verify.html', info="Registration Validation Success. Please Log in.")


class LoginHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        incorrect = self.get_secure_cookie("incorrect")
        if incorrect and int(incorrect) > 20:
            self.write('<center>blocked</center>')
            return
        if self.current_user:
            self.render('welcome.html', account_info=self.current_user)
        else:
            self.render('login.html', info="")

    @tornado.gen.coroutine
    def post(self):
        incorrect = self.get_secure_cookie("incorrect")
        if incorrect and int(incorrect) > 10:
            self.write('<center>blocked</center>')
            return

        email = self.get_argument("email")
        password = self.get_argument("password")
        account = db.Account.get_one(email=email, signup_source=db.AccountSignupSource.Site)
        try:
            if not account:
                raise errors.EmailOrPasswordNotFoundError
            if not account.check_password(password):
                raise errors.EmailOrPasswordNotFoundError
            if not account.is_active:
                raise errors.AccountInactive
            if not account.is_valid:
                raise errors.AccountNotVerified
        except Exception, e:
            incorrect = self.get_secure_cookie("incorrect") or 0
            increased = str(int(incorrect)+1)
            self.set_secure_cookie("incorrect", increased)
            self.render("login.html", info=str(e))
            return

        self.session["user_info"] = email
        self.session.save()
        self.set_secure_cookie("incorrect", "0")
        self.render("welcome.html", account_info=self.current_user)


class LogoutHandler(BaseHandler):
    def get(self):
        self.session.clear()
        self.redirect(self.get_argument("next", "/login"))