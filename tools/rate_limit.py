# coding: utf-8

import time
from functools import wraps, partial
from common import errors


class RateLimiter(object):
    def __init__(self, key_func, limit=None, period=1, send_x_headers=True, error=None):
        self.key_func = key_func

        self.limit = limit
        self.period = period

        self.send_x_headers = send_x_headers
        self.error = error or errors.RateLimitExceededError

        self.reset = None
        self.current = None

    @property
    def remaining(self):
        return self.limit - self.current

    @property
    def over_limit(self):
        return self.current > self.limit

    # decorator
    def __call__(self, view):
        @wraps(view)
        def wrapped(handler, *args, **kwargs):
            if self.limit is not None:
                self.refresh_count(handler, view)
                if self.over_limit:
                    raise self.error

            return view(handler, *args, **kwargs)

        return wrapped

    def refresh_count(self, handler, view):
        key = self.key_func(handler, view)
        self.reset = int(time.time()) + self.period

        pipe = handler.conn.redis.pipeline()
        pipe.incr(key)
        pipe.expireat(key, self.reset)
        self.current = pipe.execute()[0]

        if self.send_x_headers:
            self.set_x_headers(handler)

    def set_x_headers(self, handler):
        handler.set_header("X-RateLimit-Reset", self.reset)
        handler.set_header("X-RateLimit-Limit", self.limit)
        handler.set_header("X-RateLimit-Remaining", self.remaining)


# decorators
rate_limit_ip_global = partial(
    RateLimiter,
    key_func=lambda h, v: "rl_ip_g:%s" % h.request.remote_ip
)

rate_limit_ip_method = partial(
    RateLimiter,
    key_func=lambda h, v: "rl_ip_m:%s:%s" % (v.__name__, h.request.remote_ip)
)

rate_limit_account_global = partial(
    RateLimiter,
    key_func=lambda h, v: "rl_acc_g:%s" % h.auth.acc_id
)

rate_limit_custom_key = RateLimiter
