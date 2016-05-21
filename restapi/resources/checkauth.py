# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from .. import myself, lic, get_logger

from .base import ExtendedApiResource
from .. import htmlcodes as hcodes
from . import decorators as decorate
from confs import config

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

# TO FIX
from flask.ext.security import roles_required, auth_token_required


class Verify(ExtendedApiResource):
    """ API online test """

    @decorate.apimethod
    def get(self):
        return self.response("Hello World!")


class Login(ExtendedApiResource):
    """ Let a user login with the developer chosen method """

    @decorate.apimethod
    def get(self):
        return self.response(
            errors={"Wrong method":
                    "Please login with the POST method"},
            code=hcodes.HTTP_BAD_UNAUTHORIZED)

    @decorate.apimethod
    @decorate.load_auth_obj
    def post(self):
        """ Using a service-dependent callback """

        # This instance is obtained throught the decorator
        self._auth.make_login("test", "test2")

        return self.response(
            errors={"Todo": "work in progress"},
            code=hcodes.HTTP_BAD_UNAUTHORIZED)


class Logout(ExtendedApiResource):
    """ Let the logged user escape from here """

    @decorate.apimethod
    @auth_token_required
    def get(self):
        return self.response("Hello World!")


class VerifyLogged(ExtendedApiResource):
    """ Token authentication test """

    @decorate.apimethod
    @auth_token_required
    def get(self):
        return self.response("Valid user")


class VerifyAdmin(ExtendedApiResource):
    """ Token and Role authentication test """

    @decorate.apimethod
    @auth_token_required
    @roles_required(config.ROLE_ADMIN)
    def get(self):
        return self.response("I am admin!")
