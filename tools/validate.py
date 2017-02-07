# coding: utf-8

from functools import wraps
from common.validate import *


class RemoveArgs(object):
    def __init__(self, *args):
        schema = {}
        for arg in args:
            schema[Remove(arg)] = Nop
        self.schema = Schema(schema)

    def __call__(self, view):
        @wraps(view)
        def wrapped(handler, *args, **kwargs):
            handler.valid_arguments(schema=self.schema)
            return view(handler, *args, **kwargs)
        return wrapped


class Validation(object):
    def __init__(self, schema, required=False, extra=PREVENT_EXTRA):
        if isinstance(schema, dict):
            for key in schema:
                if key == "access_token" or getattr(key, "schema") == "access_token":
                    break
            else:
                schema.update({
                    Optional("access_token"): All(unicode, Strip),    # access_token
                })

        if not isinstance(schema, Schema):
            schema = Schema(schema, required=required, extra=extra)

        self.schema = schema

    def __call__(self, view):
        @wraps(view)
        def wrapped(handler, *args, **kwargs):
            handler.valid_arguments(schema=self.schema)
            return view(handler, *args, **kwargs)

        return wrapped
