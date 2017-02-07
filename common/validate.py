# coding: utf-8

from .voluptuous import *
import re
import uuid
from datetime import datetime
from requests.compat import quote, unquote

from .compat import json, types, integer_types, string_types, Decimal


__all__ = [
    "Required", "All", "Unique", "Set", "SetTo", "DefaultTo",
    "Strip", "Email", "Lower", "Length", "Optional", "Title", "Nop",
    "Choices", "Null", "JSON", "ToFloat", "ToInt", "Capitalize",
    "Upper", "Datetime", "Clamp", "Range", "PathExists", "IsDir",
    "IsFile", "Url", "Replace", "Match", "And", "Any", "Or", "Msg",
    "Boolean", "IsFalse", "IsTrue", "Coerce", "truth", "message", "Split",
    "Remove", "Inclusive", "Exclusive", "Marker", "Schema", "Invalid",
    "MultipleInvalid", "PREVENT_EXTRA", "ALLOW_EXTRA", "REMOVE_EXTRA",
    "MakeSafe", "CleanCR", "Quote", "UnQuote", "AfterNow", "BeforeNow",
    "ToDate", "ToDatetime", "ToDecimal", "Rename", "ToUUID",
    "Map", "Reduce", "Filter",
]


# helper functions
def ToInt(v):
    """to integer.

    >>> ToInt("1") == 1
    True
    >>> ToInt(None) == 0
    True
    >>> ToInt("123") == 123
    True
    >>> with raises(ValueInvalid):
    ...  ToInt("wrong")
    """
    try:
        if v is None:
            return 0
        if isinstance(v, integer_types):
            return v
        return types.IntType(v)
    except:
        raise ValueInvalid("Invalid Int Value")


def ToFloat(v):
    """to float.

    >>> ToFloat(".2") == .2
    True
    >>> ToFloat(None) == 0.0
    True
    >>> with raises(ValueInvalid):
    ...  ToFloat("wrong")
    """
    try:
        if v is None:
            return 0.0
        if isinstance(v, (types.FloatType,)):
            return v
        return types.FloatType(v)
    except:
        raise ValueInvalid("Invalid Float Value")


def JSON(v):
    """json loads.

    >>> JSON("{}") == {}
    True
    >>> d = {"key": "value", "key2": [1, 2, 3]}
    >>> JSON(json.dumps(d)) == d
    True
    """
    try:
        if isinstance(v, string_types):
            return json.loads(v)
        return v
    except:
        raise Invalid("Invalid JSON string")


def Strip(v):
    """Strip.

    >>> Strip("   ") == ""
    True
    >>> Strip("  a ") == "a"
    True
    """
    try:
        return v.strip()
    except Exception as e:
        raise ValueInvalid(str(e))


def Nop(v):
    """Do nothing.

    >>> Nop("value") == "value"
    True
    >>> Nop(object) == object
    True
    """
    return v


def Rename(new_name):
    """Replaced by new value.

    >>> Rename("new value")(111) == "new value"
    True
    >>> Rename(object)(111) == object
    True
    """
    @wraps(Rename)
    def f(v):
        return new_name
    return f


def Split(sep=" ", strip=True):
    """Split string to list.

    >>> Split(" ")(" 0 1 2 3 ") == map(str, range(4))
    True
    >>> Split(",")(" 0, 1 ,2, 3 ") == map(str, range(4))
    True
    """
    @wraps(Split)
    def f(v):
        if not v:
            return []
        try:
            return [(s.strip() if strip else s) for s in v.split(sep) if s]
        except:
            raise ValueInvalid("Failed Split")
    return f


def Null(v):
    """Return None.

    >>> Null(123) is None
    True
    """
    return None


def Choices(choices):
    """The value must in choices.

    >>> c = Choices([1, 2, 3])
    >>> c(1) == 1
    True
    >>> with raises(Invalid):
    ...   c(4)
    """
    @wraps(Choices)
    def f(v):
        if v not in choices:
            raise Invalid("must be one of %s" % choices)
        return v
    return f


def Email(v):
    """ check email format

    >>> e = "test@test.com"
    >>> Email(e) == e
    True
    >>> e = "test+back@test.com"
    >>> Email(e) == e
    True
    >>> e = "te-st.b_a+ck@te_st.cc.com"
    >>> Email(e) == e
    True
    >>> with raises(Invalid):
    ...   Email("123.com")
    >>> with raises(Invalid):
    ...   Email("@123.com")
    """
    if re.match("^[\w\.\-\+]+@[\w\.\-]+\.\w+$", v):
        return v
    else:
        raise Invalid("invalid email address")


def MakeSafe(v):
    """ make a string safe

    >>> s = ''' &><'{};/\/" '''
    >>> MakeSafe(s) == ' ' * len(s)
    True
    """
    return unicode(v).replace('&', ' ').replace('>', ' ').replace('<', ' ')\
        .replace("'", ' ').replace('"', ' ').replace('{', ' ').replace('}', ' ')\
        .replace(';', ' ').replace('/', ' ').replace('\\', ' ')


def CleanCR(v):
    """ Clean \r and \n

    >>> CleanCR("abc\\rdef\\n") == "abc def "
    True
    """
    return unicode(v).replace('\r', ' ').replace('\n', ' ')


def Quote(v):
    """ urllib quote

    >>> Quote("abcdef") == "abcdef"
    True
    >>> Quote("abc def") == "abc%20def"
    True
    >>> Quote(u"abc def") == "abc%20def"
    True
    >>> Quote(r"abc def") == "abc%20def"
    True
    """
    return quote(v.encode("utf-8")).decode("utf-8")


def UnQuote(v):
    """ urllib unquote

    >>> UnQuote("abc%20def") == "abc def"
    True
    >>> UnQuote(u"abc%20def") == "abc def"
    True
    >>> UnQuote(r"abc%20def") == "abc def"
    True
    """
    return unquote(v.encode("utf-8")).decode("utf-8")


def AfterNow(v):
    """Check datetime after now.

    >>> from datetime import timedelta
    >>> t1 = datetime.now() + timedelta(seconds=1)
    >>> AfterNow(t1) == t1
    True
    >>> t2 = datetime.now() - timedelta(seconds=1)
    >>> with raises(Invalid):
    ...   AfterNow(t2)
    """
    if v < datetime.now():
        raise Invalid("Invalid Datetime")
    return v


def BeforeNow(v):
    """Check datetime before now.

    >>> from datetime import timedelta
    >>> t1 = datetime.now() - timedelta(seconds=1)
    >>> BeforeNow(t1) == t1
    True
    >>> t2 = datetime.now() + timedelta(seconds=1)
    >>> with raises(Invalid):
    ...   BeforeNow(t2)
    """
    if v > datetime.now():
        raise Invalid("Invalid Datetime")
    return v


def ToDatetime(fmt="%Y-%m-%dT%H:%M:%SZ"):
    """Convert to datetime.

    >>> now = datetime.now()
    >>> t = ToDatetime("%Y-%m-%dT%H:%M:%S %f")
    >>> t(now.strftime("%Y-%m-%dT%H:%M:%S %f")) == now
    True
    """
    @wraps(ToDatetime)
    def f(v):
        try:
            return datetime.strptime(v, fmt)
        except (TypeError, ValueError):
            raise DatetimeInvalid("Invalid Datetime")
    return f


def ToDate(fmt="%Y-%m-%d"):
    """Convert to date.

    >>> now = datetime.now()
    >>> t = ToDate("%Y-%m-%d")
    >>> t(now.strftime("%Y-%m-%d")) == now.date()
    True
    """
    @wraps(ToDate)
    def f(v):
        try:
            return ToDatetime(fmt)(v).date()
        except (DatetimeInvalid,):
            raise DatetimeInvalid("Invalid Date")
    return f


def ToDecimal(v):
    """Convert to Decimal.

    >>> d = Decimal(1)
    >>> d == ToDecimal(d)
    True
    >>> d == ToDecimal(1)
    True
    >>> d == ToDecimal(1.0)
    True
    >>> Decimal(1.1) == ToDecimal(1.1)
    True
    >>> Decimal(1.1) == ToDecimal("1.1")
    False
    >>> Decimal("1234.1") == ToDecimal("1,234.1")
    True
    """
    try:
        if isinstance(v, string_types):
            v = v.replace(",", "")
        return Decimal(v)
    except:
        raise ValueInvalid("Invalid Decimal Value")


def ToUUID(v):
    """Convert to uuid.UUID.

    >>> u = uuid.uuid4()
    >>> u == ToUUID(u)
    True
    >>> u == ToUUID(u.hex)
    True
    >>> u == ToUUID(u.bytes)
    True
    >>> u == ToUUID(u.fields), u == ToUUID(list(u.fields))
    (True, True)
    >>> u == ToUUID(u.int)
    True
    """
    try:
        if isinstance(v, uuid.UUID):
            return v
        if isinstance(v, integer_types):
            return uuid.UUID(int=v)
        if isinstance(v, (tuple, list)):
            return uuid.UUID(fields=v)
        try:
            return uuid.UUID(hex=v)
        except (TypeError, ValueError):
            return uuid.UUID(bytes=v)
    except:
        raise ValueInvalid("Invalid UUID Value")


def Map(function):
    """Map a sequence.

    >>> f = lambda x: x + x
    >>> m = Map(f)
    >>> m([]) == []
    True
    >>> m([0, 2]) == [0, 4]
    True
    >>> m(range(5)) == map(f, range(5))
    True
    >>> with raises(TypeError):
    ...   m(None)
    """
    @wraps(Map)
    def f(seq):
        return map(function, seq)
    return f


def Reduce(function, initial=None):
    """Reduce a sequence.

    >>> f = lambda x, y: x + y
    >>> r = Reduce(f, 0)
    >>> r([]) is 0
    True
    >>> r([1, 2]) == 3
    True
    >>> r(range(5)) == sum(range(5))
    True
    >>> with raises(TypeError):
    ...   r(None)
    """
    @wraps(Reduce)
    def f(seq):
        if initial is None:
            return reduce(function, seq)
        else:
            return reduce(function, seq, initial)
    return f


def Filter(function):
    """Filter a sequence.

    >>> f = lambda i: i > 2
    >>> s = Filter(f)
    >>> s([]) == []
    True
    >>> s([1, 2]) == []
    True
    >>> s([1, 2, 3, 4, 5]) == [3, 4, 5]
    True
    >>> with raises(TypeError):
    ...   s(None)
    """
    @wraps(Filter)
    def f(seq):
        return filter(function, seq)
    return f


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=False)
