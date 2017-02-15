# coding: utf-8
from common.mytypes import CacheChecker


class CacheProxy(object):
    def __init__(self, client, key_template):
        self.client = client
        self.key_template = key_template

    def gen_key(self, key_args):
        return self.key_template % key_args

    def get_or_add(self, key_args, data=None, **kwargs):
        cache_key = self.gen_key(key_args)
        with CacheChecker(self.client, cache_key, **kwargs) as cached:
            if callable(data):
                data = data()
            cached.data = data

        return cached.data

    def get(self, key_args, default=None):
        cache_key = self.gen_key(key_args)
        with CacheChecker(self.client, cache_key) as cached:
            return default

        return cached.data

    def add(self, key_args, data, **kwargs):
        cache_key = self.gen_key(key_args)
        cached = CacheChecker(self.client, cache_key, **kwargs)
        if callable(data):
            data = data()
        cached.set_data(data=data)
        return data

    set = add

    def delete(self, *key_args, **key_kwargs):
        if len(key_args) == 1 and isinstance(key_args[0], dict):
            key_args = key_args[0]
        if key_kwargs:
            key_args = key_kwargs
        cache_key = self.gen_key(key_args)
        self.client.delete(cache_key)


class Cache(object):
    def __init__(self, client):
        self.client = client

        # add all cache object here
        self.user_info = CacheProxy(self.client, "user_info:%s")