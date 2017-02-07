# coding: utf-8


import os
import sys
import site


ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

prev_sys_path = list(sys.path)

# add vendor in sys.path
if os.path.exists(path("vendor")):
    sys.path.append(path("vendor"))
    for directory in os.listdir(path("vendor")):
        full_path = path("vendor/%s" % directory)
        if os.path.isdir(full_path):
            site.addsitedir(full_path)

# Move the new items to the front of sys.path
new_sys_path = []

for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)

sys.path[:0] = new_sys_path
