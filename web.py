import os.path
from environment import *   # important to setup syspath
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.autoreload
import logging
import pprint
import models
from common.mytypes import MagicDict
from basehandlers import get_cur_handler
from settings import settings, options
from urls import url_patterns
from tools.conn import Connections
from tools.bg_tasks import BackgroundTasks


class Application(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_patterns, **settings)
        self.config = MagicDict(options.as_dict())
        self.conn = Connections(self.config)
        self.bg_tasks = BackgroundTasks(self.config, self.conn)
        self.init_db()

    def init_db(self):
        models.bind_engine(self.conn.db_engine)
        models.set_scope_func(get_cur_handler)

        if not self.config["debug"]:
            return

        def close_db_engine():
            self.conn.db_engine.dispose()

        tornado.autoreload.add_reload_hook(close_db_engine)

        # init debug database
        models.drop_all(self.conn.db_engine)
        models.create_all(self.conn.db_engine)

        user = models.init_debug_data()
        self.conn.redis.flushall()


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port, options.host)
    logging.critical("Tornado server started on %s:%s" %
                     (options.host, options.port))
    pprint.pprint(url_patterns)
    tornado.ioloop.IOLoop.instance().start()