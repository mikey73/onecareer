# coding: utf-8

import os
import sys

import tornado
import tornado.util
import tornado.template

from tornado.escape import native_str
from tornado.options import define, options


# Make file paths relative to settings.
path = lambda root, *a: os.path.join(root, *a)
ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = path(ROOT, "static")
TEMPLATE_ROOT = path(ROOT, "templates")


# add tornado options
define("port", default=8888, help="run on the given port", type=int)
define("host", default="127.0.0.1", help="run on the given host")
define("conf", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")


def parse_config_file(config_file):
    config = {}
    with open(config_file, "rb") as f:
        tornado.util.exec_in(native_str(f.read()), None, config)

    for name, new_value in config.iteritems():
        if name not in options:
            define(name, default=new_value)

        if isinstance(new_value, dict):
            old_dict = options[name]
            old_dict.update(new_value)
            new_value = old_dict

        setattr(options, name, new_value)


# load options from config file
# load default.conf
parse_config_file(path(ROOT, "default.conf"))

# parse command line
tornado.options.parse_command_line(args=sys.argv)

# load --conf=xxx.conf
if options.conf:
    parse_config_file(options.conf)


# Application settings
settings = dict()
settings["debug"] = options.debug
settings["static_path"] = STATIC_ROOT
settings["cookie_secret"] = options.cookie_secret
settings["xsrf_cookies"] = options.xsrf_cookies
settings["template_loader"] = tornado.template.Loader(TEMPLATE_ROOT)
