# coding: utf-8

import os
import logging
from functools import partial

import requests
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from common import errors
from common.compat import json
from common.utils import url_join
from common.mytypes import MagicDict, APIStatus


def parse_resp(r):
    try:
        return r.json(object_hook=lambda dct: MagicDict(dct))
    except:
        raise errors.ServerHTTPError(r.code, r.body[:128])


class WrappedHTTPResponse(object):
    """ WrappedHTTPResponse, Wrap Tornado Response to requests Response """
    def __init__(self, response):
        self._resp = response

    def __getattr__(self, item):
        return getattr(self._resp, item)

    @property
    def raw(self):
        return self._resp.buffer

    @property
    def content(self):
        return self._resp.body

    @property
    def status_code(self):
        return self._resp.code

    def json(self, **kwargs):
        return json.loads(self._resp.body, **kwargs)

    def __repr__(self):
        return self._resp.__repr__()


@gen.coroutine
def do_async_fetch(method, url, data=None, files=None, headers=None, **kwargs):
    """ requests style http method using tornado AsyncHTTPClient """
    prep = requests.Request(url=url, files=files, data=data,
                            headers=headers, **kwargs).prepare()
    async_req = HTTPRequest(url, method=method, headers=prep.headers, body=prep.body)
    async_client = AsyncHTTPClient()
    resp = yield async_client.fetch(async_req)
    resp = WrappedHTTPResponse(resp)
    raise gen.Return(resp)


class AsyncClient(object):
    get = partial(do_async_fetch, "GET")
    put = partial(do_async_fetch, "PUT")
    post = partial(do_async_fetch, "POST")
    head = partial(do_async_fetch, "HEAD")
    delete = partial(do_async_fetch, "DELETE")


class AsyncAPIClient(object):
    """ AsyncAPIClient of Consult API, response is instance of MagicDict
    """
    def __init__(self, auth=None, access_token=None,
                 client_id="debug_client_id",
                 client_secret="debug_client_secret",
                 endpoint="http://localhost:9000/"):

        self._endpoint = endpoint.rstrip("/")
        self._auth = auth
        self._access_token = access_token
        self._client_id = client_id
        self._client_secret = client_secret

    def set_access_token(self, access_token):
        self._access_token = access_token

    def __getattr__(self, item):
        return AsyncAPIClient(auth=self._auth, access_token=self._access_token,
                              client_id=self._client_id,
                              client_secret=self._client_secret,
                              endpoint=url_join(self._endpoint, "/", item))

    @gen.coroutine
    def __call__(self, _method="post", auth=None, files=None, stream=False, **kwargs):
        logging.debug(self._endpoint)
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._access_token is not None:
            data["access_token"] = self._access_token
        data.update(kwargs)
        auth = auth or self._auth

        method = getattr(AsyncClient, _method.lower())
        r = yield method(self._endpoint, auth=auth, files=files, data=data)
        try:
            if stream is True:
                raise gen.Return(r)    # return response object

            content_types = [v.lower().strip() for v in r.headers.get("Content-Type", "").split(";")]
            if "application/json" not in content_types:
                raise gen.Return(r)     # return response object

            resp = parse_resp(r)
        except gen.Return:
            raise
        except:
            raise errors.ServerHTTPError(r.code, r.body[:128])

        if resp.status != APIStatus.ok:
            code = resp.code
            if code in errors.error_map:
                raise errors.error_map[code](resp.message)

            raise errors.ServerHTTPError(code, resp.message)

        raise gen.Return(resp)
