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
# from confs import config
from ..auth import auth

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


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

        username = None
        password = None
        bad_code = hcodes.HTTP_BAD_UNAUTHORIZED

        jargs = self.get_input()
        if 'username' in jargs:
            username = jargs['username']
        elif 'email' in jargs:
            username = jargs['email']
        if 'password' in jargs:
            password = jargs['password']
        elif 'pwd' in jargs:
            password = jargs['pwd']

        if username is None or password is None:
            return self.response(
                errors={"Credentials": "Missing 'username' and/or 'password'"},
                code=bad_code)

        # _auth instance is obtained throught the 'load_auth_obj' decorator
        token = self._auth.make_login(username, password)
        if token is None:
            return self.response(
                errors={"Credentials": "Invalid username and/or password"},
                code=bad_code)

        return self.response({'token': token})


class Logout(ExtendedApiResource):
    """ Let the logged user escape from here """

    @decorate.apimethod
    @auth.login_required
    def get(self):
        return self.response("Hello World!")


class VerifyLogged(ExtendedApiResource):
    """
    Token authentication test
    Example of working call is: 
    http localhost:8081/api/verifylogged Authorization:"Bearer RECEIVED_TOKEN"
    """

    @decorate.apimethod
    @auth.login_required
    def get(self):
        return self.response("Valid user")


class VerifyAdmin(ExtendedApiResource):
    """ Token and Role authentication test """

    @decorate.apimethod
    @auth.login_required
# // TO FIX:
    # @roles_required(config.ROLE_ADMIN)
    def get(self):
        return self.response("I am admin!")
