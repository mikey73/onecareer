# coding: utf-8

from functools import wraps

from tornado import log


app_log = log.app_log
gen_log = log.gen_log
access_log = log.access_log


def log_exception(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except:
            log.app_log.exception("error in %s" % method.__name__)
            raise
    return wrapped
