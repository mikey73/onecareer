# coding: utf-8

import sys
import json
import types

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from cdecimal import Decimal
except ImportError:
    from decimal import Decimal


PY2 = sys.version_info[0] == 2

try:
    from greenlet import getcurrent as get_ident
except ImportError:  # pragma: no cover
    try:
        from thread import get_ident
    except ImportError:  # pragma: no cover
        if PY2:
            from dummy_thread import get_ident
        else:
            from _dummy_thread import get_ident


_identity = lambda x: x


if not PY2:
    text_type = str
    string_types = (str,)
    integer_types = (int,)
    class_types = (type,)

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    implements_to_string = _identity

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)
    class_types = (types.TypeType, types.ClassType)

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls

    exec("def reraise(tp, value, tb=None):\n raise tp, value, tb")
