# coding: utf-8

__version__ = "0.1.1"


# import all to create metadata for Base
from .constants import *
from .base import *
from .models import *


def init_debug_data():
    """ Init debug client and users. """
    api = API.get_one(client_id="debug_client_id")
    if not api:
        api = API.new(is_admin=True, site="Consult",
                      client_id="debug_client_id",
                      client_secret="debug_client_secret")

    user = Account.get_one(email="test@consult.com")
    if not user:
        user = Account.new(email="test@consult.com",
                           password="test123",
                           fullname="test",
                           role="Talent",
                           api_pk=api.pk)
        user.is_active = True
        user.is_valid = True
        user.save()

    return api, user
