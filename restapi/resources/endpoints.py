# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import
from .. import myself, lic

from ..confs.config import AUTH_URL
from .base import ExtendedApiResource
from commons import htmlcodes as hcodes
from ..auth import authentication
from ..confs import config
# from . import decorators as decorate
from commons.logs import get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class Status(ExtendedApiResource):
    """
        API online test
    """

    def get(self):
        """
        Check if the API server is currently reachable

        You may use this URI to monitor network or server problems.
        ---
        tags:
          - status
        responses:
          200:
            description: Server is alive!
        """
        return 'Server is alive!'


class Login(ExtendedApiResource):
    """ Let a user login with the developer chosen method """

    base_url = AUTH_URL

    # @decorate.apimethod
    # def get(self):
    #     return self.send_errors(
    #         "Wrong method", "Please login with the POST method",
    #         code=hcodes.HTTP_BAD_UNAUTHORIZED)

    def post(self):
        """
        Using a service-dependent callback

        swagger_from_file: restapi/swagger/login/post.yaml
        """

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
            return self.send_errors(
                "Credentials", "Missing 'username' and/or 'password'",
                code=bad_code)

        # auth instance from the global namespace
        auth = self.global_get('custom_auth')
        token, jti = auth.make_login(username, password)
        if token is None:
            return self.send_errors(
                "Credentials", "Invalid username and/or password",
                code=bad_code)

        auth.save_token(auth._user, token, jti)

## // TO FIX
# split response as above in access_token and token_type?
# also set headers?
        # # The right response should be the following
        # # Just remove the simple response above
        # return self.force_response({
        #     'access_token': token,
        #     'token_type': auth.token_type
        # })

        """
        e.g.
{
  "scope": "https://b2stage.cineca.it/api/.*",
  "access_token": "EEwJ6tF9x5WCIZDYzyZGaz6Khbw7raYRIBV_WxVvgmsG",
  "token_type": "Bearer",
  "user": "pippo",
  "expires_in": 28800
}
        """

        return {'token': token}


class Logout(ExtendedApiResource):
    """ Let the logged user escape from here """

    base_url = AUTH_URL

    @authentication.authorization_required
    def get(self):
        auth = self.global_get('custom_auth')
        auth.invalidate_token()
        return self.empty_response()


class Tokens(ExtendedApiResource):
    """ List all active tokens for a user """

    base_url = AUTH_URL
    endkey = "token_id"
    endtype = "string"

    @authentication.authorization_required
    def get(self, token_id=None):
        auth = self.global_get('custom_auth')
        tokens = auth.get_tokens(user=auth._user)
        if token_id is None:
            return tokens

        for token in tokens:
            if token["id"] == token_id:
                return token

        errorMessage = "This token has not emitted to your account " + \
                       "or does not exist"
        return self.send_errors(
            "Token not found", errorMessage, code=hcodes.HTTP_BAD_NOTFOUND)

    @authentication.authorization_required
    def delete(self, token_id=None):
        """
            For additional security, tokens are invalidated both
            by chanding the user UUID and by removing single tokens
        """
        auth = self.global_get('custom_auth')
        user = self.get_current_user()
        tokens = auth.get_tokens(user=user)
        invalidated = False

        for token in tokens:
            # all or specific
            if token_id is None or token["id"] == token_id:
                done = auth.invalidate_token(token=token["token"], user=user)
                if not done:
                    return self.send_errors("Failed", "token: '%s'" % token)
                else:
                    logger.debug("Invalidated %s" % token['id'])
                    invalidated = True

        # Check

        # ALL
        if token_id is None:
            auth.invalidate_all_tokens(user=user)
        # SPECIFIC
        else:
            if not invalidated:
                message = "Not emitted for your account or does not exist"
                return self.send_errors(
                    "Token not found", message, code=hcodes.HTTP_BAD_NOTFOUND)

        return self.empty_response()


class TokensAdminOnly(ExtendedApiResource):
    """ Admin operations on token list """

    base_url = AUTH_URL
    endkey = "token_id"
    endtype = "string"

    @authentication.authorization_required
    def get(self, token_id):
        logger.critical("This endpoint should be restricted to admin only!")
        auth = self.global_get('custom_auth')
        token = auth.get_tokens(token_jti=token_id)
        if len(token) == 0:
            return self.send_errors(
                "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)
        return token

    @authentication.authorization_required
    def delete(self, token_id):
        logger.critical("This endpoint should be restricted to admin only!")
        auth = self.global_get('custom_auth')
        if not auth.destroy_token(token_id):
            return self.send_errors(
                "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)

        return self.empty_response()


class Profile(ExtendedApiResource):
    """ Current user informations """

    base_url = AUTH_URL

    @authentication.authorization_required
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

        return data


class Internal(ExtendedApiResource):
    """ Token and Role authentication test """

    base_url = AUTH_URL

    @authentication.authorization_required(roles=[config.ROLE_INTERNAL])
    def get(self):
        return "I am internal"


class Admin(ExtendedApiResource):
    """ Token and Role authentication test """

    base_url = AUTH_URL

    @authentication.authorization_required(roles=[config.ROLE_ADMIN])
    def get(self):
        return "I am admin!"
