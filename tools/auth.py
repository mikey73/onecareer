# coding: utf-8

from oauth2lib.provider import AuthorizationProvider as _AuthorizationProvider
from oauth2lib.provider import ResourceProvider as _ResourceProvider
from oauth2lib.provider import ResourceAuthorization as _ResourceAuthorization


class ResourceAuthorization(_ResourceAuthorization):
    acc_id = None


class ResourceProvider(_ResourceProvider):
    def __init__(self, handler):
        self.redis = handler.conn.redis
        self.handler = handler

    @property
    def authorization_class(self):
        return ResourceAuthorization

    def get_authorization_header(self):
        return self.handler.get_auth_param()

    def validate_access_token(self, access_token, authorization):
        key = AuthorizationProvider.access_template % access_token
        data = self.redis.hgetall(key)
        if data:
            ttl = self.redis.ttl(key)
            authorization.is_valid = True
            authorization.client_id = data.get("client_id")
            authorization.acc_id = data.get("acc_id")
            authorization.expires_in = ttl
            authorization.is_oauth = True
        else:
            authorization.is_oauth = False


class AuthorizationProvider(_AuthorizationProvider):
    auth_template = "oauth2:authorization_code:%s:%s"
    access_template = "oauth2:access_token:%s"
    refresh_template = "oauth2:refresh_token:%s:%s"
    client_user_template = "oauth2:client_user:%s:%s"

    def __init__(self, conn, *args, **kwargs):
        self.redis = conn.redis
        self.logged_in = False
        self.acc_id = None

    def set_user_logged(self, logged_in=False, acc_id=None):
        self.logged_in = logged_in
        self.acc_id = acc_id

    @staticmethod
    def _validate_scope(data, scope, client_id):
        valid = ((not scope or scope == data.get("scope")) and
                 (data.get("client_id") == client_id))
        return valid

    def get_token_from_post_data(self, post):
        post["redirect_uri"] = "/"
        tok = super(AuthorizationProvider, self).get_token_from_post_data(post)
        return tok

    def validate_client_id(self, client_id):
        from models import API
        return API.check_exist(client_id=client_id, is_active=True)

    def validate_client_secret(self, client_id, client_secret):
        from models import API
        return API.check_exist(client_id=client_id, client_secret=client_secret, is_active=True)

    def validate_scope(self, client_id, scope):
        return True if not scope else False

    def validate_redirect_uri(self, client_id, redirect_uri):
        return True

    def validate_access(self):
        return self.logged_in

    def validate_access_token(self, client_id, acc_id, acc_tok):
        user_key = self.client_user_template % (client_id, acc_id)
        acc_key = self.access_template % acc_tok
        return self.redis.sismember(user_key, acc_key)

    def from_authorization_code(self, client_id, code, scope):
        key = self.auth_template % (client_id, code)
        data = self.redis.hgetall(key)
        if data is None:
            return

        valid = self._validate_scope(data, scope, client_id)
        return data if valid else None

    def from_refresh_token(self, client_id, refresh_token, scope):
        key = self.refresh_template % (client_id, refresh_token)
        data = self.redis.hgetall(key)
        if data is None:
            return

        valid = self._validate_scope(data, scope, client_id)
        return data if valid else None

    def persist_authorization_code(self, client_id, code, scope, exp=60):
        key = self.auth_template % (client_id, code)
        data = {
            "client_id": client_id,
            "scope": scope,
            "acc_id": self.acc_id,
        }
        self.redis.hmset(key, data)
        self.redis.expire(key, exp)

    def persist_token_information(self, client_id, scope, access_token,
                                  token_type, expires_in, refresh_token,
                                  data):
        acc_key = self.access_template % access_token
        self.redis.hmset(acc_key, data)
        self.redis.expire(acc_key, expires_in)

        ref_key = self.refresh_template % (client_id, refresh_token)
        self.redis.hmset(ref_key, data)

        acc_id = data.get("acc_id")
        if acc_id is not None:
            key = self.client_user_template % (client_id, acc_id)
            self.redis.sadd(key, acc_key, ref_key)

        return acc_id

    def discard_authorization_code(self, client_id, code):
        key = self.auth_template % (client_id, code)
        self.redis.delete(key)

    def discard_refresh_token(self, client_id, refresh_token):
        key = self.refresh_template % (client_id, refresh_token)
        self.redis.delete(key)

    def discard_client_user_tokens(self, client_id, acc_id):
        key = self.client_user_template % (client_id, acc_id)
        pipe = self.redis.pipeline()
        members = self.redis.smembers(key)
        for member in members:
            pipe.delete(member)
        if members:
            pipe.srem(key, *members)
        pipe.execute()


def load_auth(handler):
    """ load authorization from a handler
    :param handler: a BaseHandler, must has method `get_auth_param` and conn
    :return: an instance of ResourceAuthorization
    """
    rsrc_provider = ResourceProvider(handler)
    auth = rsrc_provider.get_authorization()
    return auth

