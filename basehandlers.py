# coding: utf-8

import re
import types
import weakref
import functools
import threading
from functools import wraps
from datetime import datetime

from tornado.web import HTTPError
from tornado.web import RequestHandler
from tornado.stack_context import StackContext

from common import errors
from common.compat import (json, get_ident, string_types, class_types, iteritems)
from common.mytypes import MagicDict, APIStatus
from common.utils import json_dumps_default

from tools.log import app_log
from tools.auth import load_auth
from tools.validate import Invalid
from tools.rate_limit import rate_limit_ip_global


def get_cur_handler():
    """ get current handler saved in ThreadRequestContext,
    return current thread id if no "handler" found
    notes: context data injected in BaseHandler._execute
    """
    cur_handler = ThreadRequestContext.data.get("handler", None)
    if cur_handler is None:
        return get_ident()
    return cur_handler


class ThreadRequestContext(object):
    """A context manager that saves some per-thread state globally.
    Intended for use with Tornado's StackContext.

    Provide arbitrary data as kwargs upon creation,
    then use ThreadRequestContext.data to access it.

    see "https://gist.github.com/simon-weber/7755289"
    """

    local_state = threading.local()
    local_state.data = {}

    class MetaClass(type):
        @property
        def data(cls):
            if not hasattr(cls.local_state, "data"):
                return {}
            return cls.local_state.data

    __metaclass__ = MetaClass

    def __init__(self, **data):
        self._data = data

    def __enter__(self):
        self._prev_data = self.__class__.data
        self.__class__.local_state.data = self._data

    def __exit__(self, *exc):
        _ = exc
        self.__class__.local_state.data = self._prev_data
        del self._prev_data
        return False


class BaseHandler(RequestHandler):
    """ BaseHandler, class to collect common handler methods - all other handlers should
    subclass this one.
    """
    url_patterns = None

    def __init__(self, *args, **kwargs):
        self._form = None     # hold all flat arguments, instance of MagicDict
        super(BaseHandler, self).__init__(*args, **kwargs)

    def _execute(self, transforms, *args, **kwargs):
        """ inject global data bind to current request """
        global_data = {"handler": weakref.ref(self)}
        with StackContext(functools.partial(ThreadRequestContext, **global_data)):
            super(BaseHandler, self)._execute(transforms, *args, **kwargs)

    @rate_limit_ip_global(limit=None, period=1)     # warning: experimental method
    def prepare(self):
        super(BaseHandler, self).prepare()

    def on_finish(self):
        from models import remove_session
        remove_session()

    @property
    def conn(self):
        return self.application.conn

    @property
    def config(self):
        return self.application.config

    @property
    def bg_tasks(self):
        return self.application.bg_tasks

    @property
    def form(self):
        if self._form is None:
            self._form = self.get_flat_arguments()
        return self._form

    def render(self, template_name, **kwargs):
        """ convert dict to MagicDict and send to template """
        for key, value in iteritems(kwargs):
            if isinstance(value, dict):
                kwargs[key] = MagicDict(value)
        return super(BaseHandler, self).render(template_name, **kwargs)

    def data_received(self, chunk):
        return super(BaseHandler, self).data_received(chunk)

    def host_url(self, url=""):
        return "%s://%s%s" % (self.request.protocol, self.request.host, url)

    def get_header(self, name, default=None):
        values = self.request.headers.get_list(name)
        return values[-1] if values else default

    def get_flat_arguments(self):
        """ flat arguments if length of values is 1
        :return: MagicDict of flatten arguments
        """
        args = {}
        for name in self.request.arguments:
            values = self.get_arguments(name)
            args[name] = values[0] if len(values) == 1 else values
        return MagicDict(args)

    def valid_arguments(self, schema):
        """ call schema to valid all arguments
        :param schema: callable schema, instance of voluptuous.Schema
        :return: self._form will re-assigned to new valid flat arguments
        :raise: raise errors.SchemaInvalidError on error
        """
        try:
            self._form = MagicDict(schema(self.form))
        except Invalid as e:
            app_log.error("Invalid arguments: %s", self.form)
            raise errors.SchemaInvalidError(str(e))
        return self._form

    def get_auth_param(self):
        """ return auth string from request header or arguments,
        called by ResourceProvider
        :return: authorization string
        """
        acc_tok = self.form.pop("access_token", None)
        if acc_tok:
            return "Bearer %s" % acc_tok

        return self.get_header("Authorization", None)

    def load_api(self):
        """ load api from database, require 'client_id' and 'client_secret'
        called by required_api_client or APIHandler
        :return: instance of models.API
        :raise: APIKeyError if no api found
        """
        from models import API

        client_id = self.form.pop("client_id", None)
        client_secret = self.form.pop("client_secret", None)
        if not client_id:
            client_id = self.get_header("client_id", None)
        if not client_secret:
            client_secret = self.get_header("client_secret", None)

        #api = API.filter_one(client_id=client_id, client_secret=client_secret)
        api = API.get_one()
        if api is None:
            raise errors.APIKeyError
        return api

    def default_action(self, *args, **kwargs):
        _ = self, args, kwargs
        raise HTTPError(404)

    def _dispatch(self, *args, **kwargs):
        """ dispatch request to method specified in url_patterns.
        The url pattern format is [url pattern, method name, HTTP method(s)]
        The subclass call self._dispatch in get, post ....
        :return: method returns
        """
        patterns = getattr(self, "url_patterns", None)
        if patterns is None:
            return self.default_action(*args, **kwargs)

        for line in patterns:
            pattern, action, methods = line[0:3]    # [url pattern, method name, HTTP method(s), ... ]

            if isinstance(pattern, string_types):
                # compile str pattern to regex
                pattern = re.compile(pattern, re.DOTALL)
                line[0] = pattern    # warning: cache compiled regex back

            match = pattern.search(self.request.path)
            if match:
                if self.request.method not in methods:
                    raise HTTPError(405)

                action_func = getattr(self, action)
                if not callable(action_func):
                    return self.default_action(*args, **kwargs)
                else:
                    return action_func(*args, **kwargs)

    # http methods
    get = post = _dispatch


class JSONHandler(BaseHandler):
    """ JSONHandler, can load arguments from JSON input """

    _log_access_ = True

    def __init__(self, *args, **kwargs):
        super(JSONHandler, self).__init__(*args, **kwargs)
        self._json_arguments = None
        self._content_type_set = False
        self._json_response = {}

    def load_json(self, raise_error=True):
        """ Load JSON from the request body and store them in
        self._json_arguments, like Tornado does by default for POSTed form
        parameters.
        :param raise_error: raise error, default is True
        :return: self._json_arguments
        :raise: JsonDecodeError on error if raise_error is True
        """
        try:
            self._json_arguments = json.loads(self.request.body)
            return self._json_arguments
        except ValueError:
            if not raise_error:
                return {}
            raise errors.JsonDecodeError

    def get_json_argument(self, name, default=None):
        """Find and return the argument with key 'name' from JSON request data.
        Similar to Tornado's get_argument() method.
        """
        if default is None:
            default = self._ARG_DEFAULT

        if self._json_arguments is None:
            self.load_json()

        if name not in self._json_arguments:
            if default is self._ARG_DEFAULT:
                raise errors.MissingParameter("Missing argument '%s'" % name)
            return default
        arg = self._json_arguments[name]
        return arg

    def set_header(self, name, value):
        if name.lower() == "content-type":
            self._content_type_set = True

        super(JSONHandler, self).set_header(name=name, value=value)

    def add_header(self, name, value):
        if name.lower() == "content-type":
            self._content_type_set = True

        super(JSONHandler, self).add_header(name=name, value=value)

    def finish(self, chunk=None):
        # do not over-writen if Content-Type was set
        if not self._content_type_set:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        if self._json_response:
            data = json.dumps(self._json_response, default=json_dumps_default)
            super(JSONHandler, self).write(data)

        super(JSONHandler, self).finish(chunk)

    def write(self, resp, update=False):
        if isinstance(resp, dict):
            if update:
                self._json_response.update(resp)
            else:
                self._json_response = resp
        else:
            super(JSONHandler, self).write(resp)

    def get_flat_arguments(self):
        args = super(JSONHandler, self).get_flat_arguments()
        # add arguments loaded from json
        args.update(self.load_json(raise_error=False))
        return args

    def get_uploaded_files(self, file_key, raise_error=True):
        file_infos = self.request.files.get(file_key)
        if raise_error and not file_infos:
            raise errors.FileError("no file uploaded for [%s]" % file_key)
        return file_infos

    def write_resp(self, resp=None):
        self.write({
            "status": APIStatus.ok,
            "response": {} if (resp is None) else resp,
            "meta": {
                "status": 200,
                "msg": "OK",
            },
        })

    def write_error(self, status_code, **kwargs):
        """ override RequestHandler `write_error()`,
        set status to 200, add `code` and `message` to response
        """
        res = {
            "status": APIStatus.error,
            "code": status_code,
            "response": None,
            "message": str(self._reason),
        }
        if "exc_info" in kwargs:
            e = kwargs["exc_info"][1]
            if hasattr(e, "log_message") and e.log_message is not None:
                res["message"] = e.log_message
            else:
                res["message"] = str(e)
            if hasattr(e, "error_code"):
                res["code"] = e.error_code

            # if isinstance(e, HTTPError):
            #     res["code"] = errors.TornadoError.error_code

        res["meta"] = {
            "status": 400,
            "msg": res["message"],
            "code": res["code"],
        }
        app_log.exception("http error: %s" % str(res["meta"]))
        self.set_status(200)
        self.write(res)
        self.finish()

    def on_finish(self):
        if self._log_access_:
            req = self.request
            meta = self._json_response.get("meta", {})

            auth = getattr(self, "auth", None)
            account_pk = auth and auth.acc_id

            self.bg_tasks.log_api_access(
                account_pk=account_pk,
                path=req.path,
                method=req.method,
                start_ts=datetime.utcfromtimestamp(req._start_time),
                runtime=req.request_time(),
                status=meta.get("status", self.get_status()),
                msg=meta.get("msg", ""),
                error_code=meta.get("code", None)
            )

        super(JSONHandler, self).on_finish()


class NotFoundHandler(JSONHandler):
    """ NotFoundHandler, raise 404 for all requests"""
    def get(self, *args, **kwargs):
        raise HTTPError(404)

    head = post = delete = patch = put = options = get


class APIHandler(JSONHandler):
    """ APIHandler, `client_id` and `client_secret` required for all requests """
    def __init__(self, *args, **kwargs):
        super(APIHandler, self).__init__(*args, **kwargs)
        self.api = None

    def prepare(self):
        """ load api, raise APIKeyError if failed """
        super(APIHandler, self).prepare()
        self.api = self.load_api()


def required_api_client(method):
    """ decorator for api client check,
    add `api` to handler if passed, it's an instance of models.API
    :param method: a method of a handler
    :return: an wrapped method that call load_api before,
    :raise: APIKeyError if failed
    """
    @wraps(method)
    def wrapped(handler, *args, **kwargs):
        handler.api = handler.load_api()
        return method(handler, *args, **kwargs)
    return wrapped


class AuthRequiredHandler(APIHandler):
    _api_required_ = False

    """ AuthRequiredHandler, auth info required for all request """
    def __init__(self, *args, **kwargs):
        super(AuthRequiredHandler, self).__init__(*args, **kwargs)
        self.auth = None

    def prepare(self):
        """ check auth info, raise AuthError if failed """
        try:
            # try to load api
            super(AuthRequiredHandler, self).prepare()
        except errors.APIKeyError:
            if self._api_required_:
                raise
            # ignore error in load_api

        auth = load_auth(self)
        if auth and auth.is_oauth:
            self.auth = auth
        else:
            raise errors.AuthError

    def get_cur_account(self, **filters):
        """ get account bind to auth.acc_id from database,
        is_active and is_valid must be True
        :param filters: ext filters for DB search
        :return: current account
        :raise: errors.AccountPermissionError
        """
        import models as db
        try:
            return db.Account.get_and_check(pk=self.auth.acc_id,
                                            is_active=True,
                                            is_valid=True,
                                            **filters)
        except errors.APIError:
            raise errors.AccountPermissionError


def required_auth(method):
    """ decorator for OAuth2 authorization,
    add `auth` to handler if passed, it's an instance of ResourceAuthorization
    :param method: a method of a handler
    :return: an wrapped method that call load_auth before
    :raise: AuthError if auth failed
    """
    @wraps(method)
    def wrapped(handler, *args, **kwargs):
        auth = load_auth(handler)
        if auth and auth.is_oauth:
            handler.auth = auth
            return method(handler, *args, **kwargs)
        else:
            raise errors.AuthError
    return wrapped


def get_url_patterns(prefix="", handlers=None, module=None):
    """ gather RequestHandlers and make url patterns
    :param prefix: url prefix
    :param handlers: list of RequestHandlers
    :param module: a module has RequestHandlers or 'url_patterns'
    :return: list of Tornado style url patterns [(pattern, HandlerClass), ...]
    """
    patterns = []

    if not module and not handlers:
        return patterns

    if not handlers:
        handlers = []

    # gather from a module
    if isinstance(module, types.ModuleType):
        if hasattr(module, "url_patterns"):
            url_patterns = getattr(module, "url_patterns")
            print "url_patterns:"
            print url_patterns
            patterns.extend([(prefix + url, handler) for url, handler in url_patterns])
        else:
            handlers.extend(module.__dict__.values())

    # gather from handlers
    for obj in handlers:
        if isinstance(obj, class_types) and issubclass(obj, RequestHandler):
            url_patterns = getattr(obj, "url_patterns", None)
            if url_patterns is not None:
                if not isinstance(url_patterns, (list, tuple)):
                    url_patterns = [url_patterns]

                # url_patterns is list
                for pattern in url_patterns:
                    # The format is [url pattern, method name, HTTP method(s)]
                    pattern = pattern[0]   # first is string pattern
                    if not isinstance(pattern, string_types):
                        raise TypeError("%s: pattern must be string types instead of %s" %
                                        (obj, type(pattern)))
                    patterns.append((prefix + pattern, obj))

    return patterns
