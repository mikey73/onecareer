# coding: utf-8

import inspect
import json

from .compat import *


class MagicDict(dict):
    def __init__(self, *args, **kwargs):
        super(MagicDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class JSONInfo(MagicDict):
    _fields_ = {}
    _valid_ = None

    def __init__(self, *args, **kwargs):
        super(JSONInfo, self).__init__(*args, **kwargs)

    @classmethod
    def fields(cls):
        return cls._fields_.keys()

    @classmethod
    def from_json(cls, json_str, *args, **kwargs):
        return cls(json.loads(json_str, *args, **kwargs))

    loads = from_json

    @classmethod
    def from_dict(cls, data, valid=None, init_default=False):
        valid = valid or cls._valid_
        if callable(valid):
            data = valid(data)

        obj = cls(data)

        if init_default:
            obj.init_default()

        return obj

    def init_default(self):
        for name, default in self._fields_.iteritems():
            if name not in self:
                if callable(default):
                    self[name] = default()
                else:
                    self[name] = default

    def to_json(self, strict=True, exclude=None, **kwargs):
        if exclude is None:
            exclude = []

        d = {}
        for key, value in self.__dict__.iteritems():
            if key.startswith("_") or callable(value):
                continue
            if key in exclude:
                continue
            if strict and key not in self._fields_:
                continue
            d[key] = value

        return json.dumps(d, **kwargs)

    dumps = to_json


class CachedProperty(object):
    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value

cached_property = CachedProperty


# warning: experimental module
class CacheChecker(object):
    """ CacheChecker, Context Manager of cache data,
    skip with block if data get from cached.
    default serializing is pickle

    Example usage::

        client = redis.StrictRedis(...)
        key = "id"

        # code block inside will be skipped if cache found
        with CacheChecker(client, key, ex=2) as cached:
            # not found
            data = do_something(...)

            # set and cache data
            cached.data = data


        print(cached.data)

    """

    class CacheFound(Exception):
        pass

    def __init__(self, cache_client, key,
                 loads_func=None, dumps_func=None,
                 *args, **kwargs):
        self.cache_client = cache_client
        self.key = key
        self._args = args        # used by cache_client.set
        self._kwargs = kwargs    # used by cache_client.set
        self._data = None
        self._loads = pickle.loads if loads_func is None else loads_func
        self._dumps = pickle.dumps if dumps_func is None else dumps_func

    def __nonzero__(self):
        return self._data is not None

    def __enter__(self):
        self._data = self.cache_client.get(self.key)

        if self._data is not None:
            # noinspection PyBroadException
            try:
                self._data = self._loads(self._data)
            except:
                return self    # loads failed

            # cache found, skip with block
            self._org_trace = sys.gettrace()
            sys.settrace(lambda *args, **kwargs: None)
            frame = inspect.currentframe(1)
            frame.f_trace = self.f_trace

        return self

    def __exit__(self, _type, value, traceback):
        if hasattr(self, "_org_trace"):
            sys.settrace(self._org_trace)

        if (_type is None) and (value is None) and (traceback is None):
            return True     # no exception

        if (isinstance(value, CacheChecker.CacheFound) or
                (isinstance(_type, class_types) and issubclass(_type, CacheChecker.CacheFound))):
            return True     # skip exception CacheFound
        else:
            reraise(_type, value, traceback)

    def f_trace(self, frame, event, arg):
        raise self.CacheFound

    def get_data(self):
        return self._data

    def set_data(self, data, dumps_func=None):
        self._data = data
        if dumps_func is None:
            dumps_func = self._dumps
        str_data = dumps_func(data)
        self.cache_client.set(self.key, str_data, *self._args, **self._kwargs)

    data = property(fget=get_data, fset=set_data, doc="Data")


class APIStatus(object):
    ok = "ok"
    error = "error"
