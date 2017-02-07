# coding: utf-8

import socket
import smtplib
from ssl import SSLError
from email.mime.text import MIMEText
from tornado import gen

from common.mytypes import MagicDict


class EmailClient(object):
    def __init__(self, config, prefix=""):
        self.config = MagicDict()
        for key in config:
            if key.startswith(prefix):
                self.config[key[len(prefix):]] = config[key]

    @gen.coroutine
    def create_client(self):
        try:
            _client = smtplib.SMTP_SSL(host=self.config.host,
                                       port=self.config.port,
                                       timeout=self.config.timeout)
        except SSLError:
            _client = smtplib.SMTP(host=self.config.host,
                                   port=self.config.port,
                                   timeout=self.config.timeout)

        if self.config.use_tls:
            _client.starttls()
            _client.ehlo()

        if self.config.username and self.config.password:
            _client.login(self.config.username, self.config.password)

        raise gen.Return(_client)

    @gen.coroutine
    def send_mail(self, sender, to_addrs, subject, msg, **kwargs):
        msg = MIMEText(msg, **kwargs)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ",".join(to_addrs)

        client = yield gen.Task(self.create_client)
        try:
            client.sendmail(sender, to_addrs, msg.as_string())
            client.quit()
        except socket.sslerror:
            client.close()
            raise
        except:
            raise

        raise gen.Return(True)
