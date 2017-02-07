# coding: utf-8

import os
import logging
import tempfile

from ..mytypes import MagicDict


class AWSClient(object):
    def __init__(self, config, prefix=""):
        self.config = MagicDict()
        for key in config:
            if key.startswith(prefix):
                self.config[key[len(prefix):]] = config[key]

        if self.config.debug_local:
            self.local_dir = tempfile.gettempdir()
        else:
            import boto3

            logging.getLogger("boto3").setLevel(logging.CRITICAL)

            self.s3 = boto3.resource(
                "s3",
                region_name=self.config.region_name,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key
            )
            self.region_name = self.config.region_name
            self.s3_buckets = {}

    def get_bucket(self, bucket_name=None):
        if bucket_name is None:
            bucket_name = self.config.s3_bucket

        if bucket_name not in self.s3_buckets:
            # noinspection PyBroadException
            try:
                self.s3.meta.client.head_bucket(Bucket=bucket_name)
                s3_bucket = self.s3.Bucket(bucket_name)
            except:
                s3_bucket = self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": self.region_name,
                    }
                )
            self.s3_buckets[bucket_name] = s3_bucket

        return self.s3_buckets[bucket_name]

    def save_to_s3(self, key, content, bucket_name=None):
        if bucket_name is None:
            bucket_name = self.config.s3_bucket

        if self.config.debug_local:
            file_name = os.path.join(self.local_dir, bucket_name, key)
            file_name = os.path.abspath(file_name)
            file_dir = os.path.dirname(file_name)
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)

            logging.info("save to temp file: %s" % file_name)

            with open(file_name, "wb") as f:
                f.write(content)
        else:
            logging.info("save %s to S3 bucket %s" % (key, bucket_name))
            self.get_bucket(bucket_name).put_object(Key=key, Body=content)

    def delete_s3_files(self, keys, bucket_name=None):
        if not isinstance(keys, (set, tuple, list)):
            keys = [keys]

        if bucket_name is None:
            bucket_name = self.config.s3_bucket

        if self.config.debug_local:
            for key in keys:
                file_name = os.path.join(self.local_dir, bucket_name, key)
                file_name = os.path.abspath(file_name)
                logging.info("remove temp file: %s" % file_name)
                if os.path.isfile(file_name):
                    os.remove(file_name)
        else:
            logging.info("delete %s in S3 bucket %s" % (keys, bucket_name))
            self.s3.Bucket(bucket_name).delete_objects(
                Delete={
                    "Objects": [{"Key": key} for key in keys]
                }
            )

    def get_s3_file(self, key, bucket_name=None, stream=False):
        if bucket_name is None:
            bucket_name = self.config.s3_bucket
        if self.config.debug_local:
            file_name = os.path.join(self.local_dir, bucket_name, key)
            file_name = os.path.abspath(file_name)
            logging.info("read temp file: %s" % file_name)
            if stream:
                return open(file_name, "rb")

            # else:
            with open(file_name, "rb") as f:
                return f.read()
        else:
            logging.info("read %s from S3 bucket %s" % (key, bucket_name))
            response = self.s3.Object(bucket_name=bucket_name, key=key).get()
            if stream:
                return response["Body"]
            else:
                return response["Body"].read()
