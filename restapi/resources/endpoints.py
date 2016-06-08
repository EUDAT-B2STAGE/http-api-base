# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import division, absolute_import
from .. import myself, lic, get_logger

from confs.config import AUTH_URL
from .base import ExtendedApiResource
from commons import htmlcodes as hcodes
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

    @decorate.apimethod
    def post(self):
        """ Using a service-dependent callback """

        # # In case you need different behaviour when using unittest:
        # if current_app.config['TESTING']:
        #     print("\nThis is inside a TEST\n")

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

        # auth instance from the global namespace
        auth = self.global_get('custom_auth')
        token = auth.make_login(username, password)
        if token is None:
            return self.response(
                errors={"Credentials": "Invalid username and/or password"},
                code=bad_code)

## TO FIX
# RESPONSE SHOULD BE:
#  {
#       'access_token': '9tiAF8Wozt0ACd-Aum3IKoAKuFlYt4A7ajZBTDyaoYk',
#       'token_type': 'Bearer'
#  }
        auth.save_token(auth._user, token)

        return self.response({'token': token})


class Logout(ExtendedApiResource):
    """ Let the logged user escape from here """

    base_url = AUTH_URL

    @auth.login_required
    @decorate.apimethod
    def get(self):
        auth = self.global_get('custom_auth')
        auth.invalidate_token()
        return self.response("", code=hcodes.HTTP_OK_NORESPONSE)


class Tokens(ExtendedApiResource):
    """ List all active tokens for a user """

    base_url = AUTH_URL
    endkey = "token_id"
    endtype = "int"

    @auth.login_required
    @decorate.apimethod
    def get(self):
        auth = self.global_get('custom_auth')
        tokens = auth.list_all_tokens(auth._user)
        return self.response(tokens)

    @auth.login_required
    @decorate.apimethod
    def delete(self, token_id=None):
        auth = self.global_get('custom_auth')
        tokens = auth.list_all_tokens(auth._user)

        if token_id is None:
            """
                For additional security, tokens are invalidated both
                by chanding the user UUID and by removing single tokens
            """
            for token in tokens:
                auth.invalidate_token(token=token["token"])
            auth.invalidate_all_tokens()

            return self.response("", code=hcodes.HTTP_OK_NORESPONSE)
        else:
            for token in tokens:
                if token["id"] == token_id:
                    auth.invalidate_token(token=token["token"])
                    return self.response("", code=hcodes.HTTP_OK_NORESPONSE)

            errorMessage = "This token has not emitted to your account " + \
                           "or does not exist"
            return self.response(
                "", errors=[{"Token not found": errorMessage}])


class Profile(ExtendedApiResource):
    """ Current user informations """

    base_url = AUTH_URL

    @auth.login_required
    @decorate.apimethod
    def get(self):
        """
        Token authentication tester. Example of working call is: 
        http localhost:8081/api/verifylogged
            Authorization:"Bearer RECEIVED_TOKEN"
        """

        auth = self.global_get('custom_auth')
        print("DEBUG PROFILE", auth._user, auth._payload)
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
