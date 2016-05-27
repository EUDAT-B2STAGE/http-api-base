# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import division, absolute_import
from .. import myself, lic, get_logger

from flask import current_app
from confs.config import AUTH_URL
from .base import ExtendedApiResource
from .. import htmlcodes as hcodes
from . import decorators as decorate
from ..auth import auth
# from confs import config

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class Status(ExtendedApiResource):
    """ API online test """

    @decorate.apimethod
    def get(self):
        return self.response("Server is alive!")


class Login(ExtendedApiResource):
    """ Let a user login with the developer chosen method """

    base_url = AUTH_URL

    @decorate.apimethod
    def get(self):
        return self.response(
            errors={"Wrong method":
                    "Please login with the POST method"},
            code=hcodes.HTTP_BAD_UNAUTHORIZED)

    @decorate.load_auth_obj
    @decorate.apimethod
    def post(self):
        """ Using a service-dependent callback """

        if current_app.config['TESTING']:
            print("\n\n\nThis is inside a TEST\n\n\n")

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

    base_url = AUTH_URL

    @auth.login_required
    @decorate.load_auth_obj
    @decorate.apimethod
    def get(self):
# TO FIX
        logger.critical("To be completed. Invalidate JWT.")
        print("DEBUG LOGOUT", self._auth._user, self._auth._payload)
        return self.response("", code=hcodes.HTTP_OK_NORESPONSE)


class Profile(ExtendedApiResource):
    """ Current user informations """

    base_url = AUTH_URL

    @auth.login_required
    @decorate.load_auth_obj
    @decorate.apimethod
    def get(self):
        """
        Token authentication tester. Example of working call is: 
        http localhost:8081/api/verifylogged
            Authorization:"Bearer RECEIVED_TOKEN"
        """
        print("DEBUG", self._auth._user, self._auth._payload)
        return self.response("Valid user")

    """
    user = User.query.get(int(tokenizer.user_id))
    roles = ""
    for role in user.roles:
        roles += role.name + '; '
    response = {
        'Name': user.first_name,
        'Surname': user.last_name,
        'Email': user.email,
        'Roles': roles
    }
    """


# class Admin(ExtendedApiResource):
#     """ Token and Role authentication test """

#     base_url = AUTH_URL

#     @auth.login_required
#     @decorate.apimethod
# # // TO FIX:
#     # @roles_required(config.ROLE_ADMIN)
#     def get(self):
#         return self.response("I am admin!")
