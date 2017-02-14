# coding: utf-8

import redis
import tornadoredis
from sqlalchemy import engine_from_config

from common.mytypes import cached_property
from common.tools.aws import AWSClient

from .mail import EmailClient
from .cache import Cache


class Connections(object):

    def __init__(self, config):
        self.config = config

    @cached_property
    def mail_client(self):
        return EmailClient(self.config, prefix="email_")

    @cached_property
    def aws_client(self):
        return AWSClient(self.config, prefix="aws_")

    @cached_property
    def db_engine(self):
        # remove unsupported db settings
        if self.config["db_url"].startswith("sqlite:"):
            self.config.pop("db_pool_size", None)
        return engine_from_config(self.config, prefix="db_")

    @cached_property
    def db_session(self):
        from ocrolus_api.models import global_session
        return global_session

    @cached_property
    def redis(self):
        return redis.StrictRedis(**self.config["redis_options"])


