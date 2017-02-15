# coding: utf-8

import re
import types
import weakref
import functools
import threading

from tornado.web import HTTPError
from tornado.web import RequestHandler
from tornado.stack_context import StackContext

from common import errors
from common.compat import (get_ident, string_types, class_types, iteritems)
from common.mytypes import MagicDict

from tools.log import app_log
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

    def get_current_user(self):
        return self.conn.cache.user_info.get(key_args=self.get_secure_cookie("user_pk"))

    def is_login(self):
        if self.current_user:
            return True
        return False

    def get_cur_account(self, **filters):
        """ get account bind to auth.acc_id from database,
        is_active and is_valid must be True
        :param filters: ext filters for DB search
        :return: current account
        :raise: errors.AccountPermissionError
        """
        import models as db
        try:
            return db.Account.get_and_check(pk=int(self.get_secure_cookie("user_pk")),
                                            is_active=True,
                                            is_valid=True,
                                            **filters)
        except errors.APIError:
            raise errors.AccountPermissionError

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
