# coding: utf-8

import os
import uuid
import base64
import hashlib
from hmac import HMAC
from datetime import date, datetime

from .compat import text_type, string_types


def to_utf8(s, errors="strict"):
    if isinstance(s, text_type):
        return s.encode("utf-8", errors=errors)
    return s


def gen_uuid_str(prefix="", length=8):
    # todo: generate real unique ID
    uuid_str = str(uuid.uuid4().get_hex())
    while length > len(uuid_str):
        uuid_str += str(uuid.uuid4().get_hex())
    return prefix + uuid_str[:length]


def gen_random_str(length=16):
    return base64.b64encode(os.urandom(length))[:length]


def gen_md5(content):
    return hashlib.md5(content).hexdigest()


def gen_sha256(content):
    return hashlib.sha256(content).hexdigest()


def secret_hash(source, salt=None, key="", salt_len=32):
    if salt is None:
        salt = gen_uuid_str(length=salt_len)
    else:
        salt = to_utf8(salt)
        salt = salt[:salt_len]

    source = to_utf8(source)
    key = to_utf8(key)
    result = source + key
    for i in range(8):
        result = HMAC(result, salt, hashlib.sha256).hexdigest()
    return salt + result


def url_join(base, *args):
    if not args:
        return base
    if not base.endswith("/"):
        base += "/"
    return base + "/".join(map(lambda s: str(s).rstrip("/"), args)).lstrip("/")


def iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True


def lists_to_dict(keys, values):
    return dict(zip(keys, values))


def flat_arguments(args_dict):
    args = {}
    for name in args_dict:
        values = args_dict.get(name)
        args[name] = values[0] if len(values) == 1 else values
    return args


JSON_DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
]

JSON_DATETIME_STR_LENS = [20, 10]


def json_dumps_default(item):
    if isinstance(item, datetime):
        return item.strftime(JSON_DATETIME_FORMATS[0])
    elif isinstance(item, date):
        return item.strftime(JSON_DATETIME_FORMATS[1])
    elif isinstance(item, uuid.UUID):
        return item.hex
    return item


# noinspection PyBroadException
def json_loads_datetime(date_str):
    if isinstance(date_str, string_types):
        for i, length in enumerate(JSON_DATETIME_STR_LENS):
            if len(date_str) == length:
                try:
                    return datetime.strptime(date_str, JSON_DATETIME_FORMATS[i])
                except:
                    pass

    return date_str


def calculate_levenshtein_distance(string1, string2):
    """ Calculates the Levenshtein distance using the
    `Iterative with two matrix rows
    <http://en.wikipedia.org/wiki/Levenshtein_distance#Iterative_with_two_matrix_rows/>`_ .
    :return: Levenshtein distance between string1 and string2
    """
    if string1 == string2:
        return 0
    if not len(string1):
        return len(string2)
    if not len(string2):
        return len(string1)

    work_vector0 = xrange(len(string2) + 1)
    work_vector1 = []
    temp_distance = 0
    for i, char1 in enumerate(string1):
        work_vector1.append(i + 1)
        for j, char2 in enumerate(string2):
            cost = 0 if char1 == char2 else 1
            work_vector1.append(min(work_vector1[j] + 1,
                                    work_vector0[j + 1] + 1,
                                    work_vector0[j] + cost))

        work_vector0 = [char for char in work_vector1]
        temp_distance = work_vector1[-1]
        work_vector1 = []

    return float(temp_distance)


def calculate_cer(string1, string2):
    """Calculates the character error rate (currently the word error rate) which is
    defined as the Levenshtein distance / the maximum possible Levenshtein distance.
    :return: The character error rate
    """
    if string1 and string2:
        l_dis = calculate_levenshtein_distance(string1, string2)
        return l_dis / (max(len(string1), len(string2)))
    elif not (string1 or string2):
        return 1
    else:
        return 0


def bbox_combine(bbox1, bbox2):
    if not bbox1:
        return bbox2
    if not bbox2:
        return bbox1

    new_bbox = list(bbox1)
    if new_bbox[0] > bbox2[0]:
        new_bbox[0] = bbox2[0]
    if new_bbox[1] > bbox2[1]:
        new_bbox[1] = bbox2[1]
    if new_bbox[2] < bbox2[2]:
        new_bbox[2] = bbox2[2]
    if new_bbox[3] < bbox2[3]:
        new_bbox[3] = bbox2[3]
    return tuple(new_bbox)


def bbox_compare(bbox1, bbox2, threshold=75):
    x_range1 = bbox1[2] - bbox1[0]
    x_range2 = bbox2[2] - bbox2[0]
    total = x_range1 + x_range2
    used1 = max(bbox1[0], bbox2[0])
    used2 = min(bbox1[2], bbox2[2])
    used = (used2 - used1) * 2
    unused = total - used
    return ((float(unused) / total) * 100) < (100 - threshold)
