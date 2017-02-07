# coding: utf-8

from concurrent import futures
from tornado import gen
from tornado.concurrent import run_on_executor as _run_on_executor

from .log import log_exception


# add logging
def run_on_executor(method):
    return _run_on_executor(log_exception(method))


class BackgroundTasks(object):
    """ BackgroundTasks, tasks running on ThreadPoolExecutor"""
    def __init__(self, config, conn):
        self.config = config
        self.conn = conn
        self.executor._max_workers = self.config.executor_max_workers

    # helper methods definition here
    # ...

    @classmethod
    def split_remote_alias(cls, remote_alias):
        # noinspection PyBroadException
        try:
            bucket_name, s3_key = remote_alias.split("::", 1)
        except:
            # set bucket_name to None to use default bucket
            bucket_name, s3_key = None, remote_alias

        return bucket_name, s3_key

    @classmethod
    def join_remote_alias(cls, bucket, s3_key):
        return "%s::%s" % (bucket, s3_key)     # add bucket_name

    ##################################################
    # BackGround Tasks
    # warning: background tasks running on executor
    ##################################################
    executor = futures.ThreadPoolExecutor(max_workers=8)

    @run_on_executor
    def send_mail(self, sender, to_addrs, subject, msg, **kwargs):
        return self.conn.mail_client.send_mail(sender, to_addrs, subject, msg, **kwargs)

    @run_on_executor
    def read_s3_file(self, remote_alias, stream=False):
        bucket_name, s3_key = self.split_remote_alias(remote_alias)
        return self.conn.aws_client.get_s3_file(s3_key, bucket_name, stream=stream)

    @run_on_executor
    def delete_s3_files(self, keys, bucket_name):
        self.conn.aws_client.delete_s3_files(keys, bucket_name)

    @run_on_executor
    @gen.coroutine
    def send_s3_file(self, handler, remote_alias, block_size=1 * 1024 * 1024):
        bucket_name, s3_key = self.split_remote_alias(remote_alias)

        file_stream = self.conn.aws_client.get_s3_file(s3_key, bucket_name, stream=True)

        while True:
            data = file_stream.read(block_size)
            if not data:
                return
            handler.write(data)

    @run_on_executor
    def log_api_access(self, **kwargs):
        import models as db

        log = db.APILog.create(**kwargs)
        log.save(commit=True)
