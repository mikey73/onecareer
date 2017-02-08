# coding: utf-8

import apis, views
from basehandlers import get_url_patterns, IndexHandler


# gather url_patterns from modules
url_patterns = []
url_patterns += get_url_patterns(prefix="/", module=views)
url_patterns += get_url_patterns(prefix="/api/v1/", module=apis)

# add default error handler at the end
url_patterns.append((".*", IndexHandler))
