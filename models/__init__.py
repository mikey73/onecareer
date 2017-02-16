# coding: utf-8

__version__ = "0.1.1"


# import all to create metadata for Base
from .constants import *
from .base import *
from .models import *


def init_debug_data():
    """ Init debug client and users. """

    user = Account.get_one(email="test@consult.com")
    if not user:
        user = Account.new(email="test@consult.com",
                           password="test123",
                           fullname="test",
                           role="Talent")
        user.is_active = True
        user.is_valid = True
        user.save()

    print user.to_dict()

    return user
