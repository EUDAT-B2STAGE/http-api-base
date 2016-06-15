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
        token, jti = auth.make_login(username, password)
        if token is None:
            return self.response(
                errors={"Credentials": "Invalid username and/or password"},
                code=bad_code)

        auth.save_token(auth._user, token, jti)

        return self.response({'token': token})

        # The right response should be the following
        # Just remove the simple response above
        return self.response({
                             'access_token': token,
                             'token_type': auth.token_type
                             })


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
    endtype = "string"

    @auth.login_required
    @decorate.apimethod
    def get(self, token_id=None):
        auth = self.global_get('custom_auth')
        tokens = auth.get_tokens(user=auth._user)
        if token_id is None:
            return self.response(tokens)

        for token in tokens:
            if token["id"] == token_id:
                return self.response(token)

        errorMessage = "This token has not emitted to your account " + \
                       "or does not exist"
        return self.response(errors=[{"Token not found": errorMessage}],
                             code=hcodes.HTTP_BAD_NOTFOUND)

    @auth.login_required
    @decorate.apimethod
    def delete(self, token_id=None):
        auth = self.global_get('custom_auth')
        tokens = auth.get_tokens(user=auth._user)

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
            return self.response(errors=[{"Token not found": errorMessage}],
                                 code=hcodes.HTTP_BAD_NOTFOUND)


class TokensAdminOnly(ExtendedApiResource):
    """ Admin operations on token list """
    @auth.login_required
    @decorate.apimethod
    def delete(self, token_id):
        auth = self.global_get('custom_auth')
        tokens = auth.get_tokens(token_jti=token_id)
        return self.response(tokens)


class Profile(ExtendedApiResource):
    """ Current user informations """

    base_url = AUTH_URL

    @auth.login_required
    @decorate.apimethod
    def get(self):
        """
        Token authentication tester. Example of working call is: 
        http localhost:8081/auth/profile
            Authorization:"Bearer RECEIVED_TOKEN"
        """

        auth = self.global_get('custom_auth')
        data = {}
        data["status"] = "Valid user"
        data["email"] = auth._user.email

        roles = []
        for role in auth._user.roles:
            roles.append(role.name)
        data["roles"] = roles

        if hasattr(auth._user, 'name'):
            data["name"] = auth._user.name

        if hasattr(auth._user, 'surname'):
            data["surname"] = auth._user.surname

        if hasattr(auth._user, 'irods_user'):
            data["irods_user"] = auth._user.irods_user

        return self.response(data)

# class Admin(ExtendedApiResource):
#     """ Token and Role authentication test """

#     base_url = AUTH_URL

#     @auth.login_required
#     @decorate.apimethod
# # // TO FIX:
#     # @roles_required(config.ROLE_ADMIN)
#     def get(self):
#         return self.response("I am admin!")
