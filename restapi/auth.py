# -*- coding: utf-8 -*-

"""
The tokens used are RFC6750 Bearer tokens.

The Resource should validate the tokens using the token validation endpoint;
its basic use is by adding
'Authorization: Bearer ' + tokenString to the HTTP header;
cf. RFC6749 section 7.1.

Note that anyone can validate a token as it is a bearer token:
there is no client id nor is client authentication required.
"""

from __future__ import division, absolute_import

from functools import wraps
from flask import request, g
from commons import htmlcodes as hcodes
from commons.meta import Meta
from commons.decorators import class_method_decorator_with_optional_parameters
from commons.logs import get_logger
from . import myself, lic

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

# Few costants
HTTPAUTH_DEFAULT_SCHEME = "Bearer"
HTTPAUTH_DEFAULT_REALM = "Authentication Required"
HTTPAUTH_TOKEN_KEY = 'Token'
HTTPAUTH_AUTH_HEADER = 'WWW-Authenticate'
HTTPAUTH_AUTH_FIELD = 'Authorization'


class HTTPTokenAuth(object):
    """
    Our class to implement a Generic Token (oauth2-like)
    authentication. Some copy/paste from:
https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/master/flask_httpauth.py
    """
    def __init__(self, scheme=None, realm=None):
        self._scheme = scheme or HTTPAUTH_DEFAULT_SCHEME
        self._realm = realm or HTTPAUTH_DEFAULT_REALM

    def authenticate_header(self):
        return '{0} realm="{1}"'.format(self._scheme, self._realm)

    def authenticate(self, verify_token_callback, token):
        if verify_token_callback:
            return verify_token_callback(token)
        return False

    @staticmethod
    def get_authentication_from_headers():
        """
        Returns (auth, token)
        """
        return request.headers.get(HTTPAUTH_AUTH_FIELD).split(None, 1)

    def authenticate_roles(self, verify_roles_callback, roles):
        if verify_roles_callback:
            return verify_roles_callback(roles)
        return False

    def get_auth_from_header(self):

        # If token is unavailable, clearly state it in response to user
        token = "EMPTY"
        auth_type = None

        auth = request.authorization
        if auth is None and HTTPAUTH_AUTH_FIELD in request.headers:
            # Flask/Werkzeug do not recognize any authentication types
            # other than Basic or Digest, so here we parse the header by hand
            try:
                auth_type, token = self.get_authentication_from_headers()
            except ValueError:
                # The Authorization header is either empty or has no token
                pass

        return auth_type, token

    # TODO: check if we can now remove this decorator
    # to use authorization_required as a simple decorator
    @class_method_decorator_with_optional_parameters
    def authorization_required(self, f, roles=[], from_swagger=False):
        @wraps(f)
        def decorated(*args, **kwargs):

            # Recover the auth object
            auth_type, token = self.get_auth_from_header()
            # Base header for errors
            headers = {HTTPAUTH_AUTH_HEADER: self.authenticate_header()}
            bad_code = hcodes.HTTP_BAD_UNAUTHORIZED
            # Internal API 'self' reference
            decorated_self = Meta.get_self_reference_from_args(*args)

            if auth_type is None or auth_type.lower() != self._scheme.lower():
                # Wrong authentication string
                msg = "Please provide valid credentials " + \
                      "inside HEADERS in the form of '%s': '%s %s'" % \
                      (HTTPAUTH_AUTH_FIELD, HTTPAUTH_DEFAULT_SCHEME, 'TOKEN')
                #
                return decorated_self.send_errors(
                    label="No authentication schema",
                    message=msg, headers=headers, code=bad_code)

            # Handling OPTIONS forwarded to our application:
            # ignore headers and let go, avoid unwanted interactions with CORS
            if request.method != 'OPTIONS':

                # Check authentication
                token_fn = g._custom_auth.verify_token
                if not self.authenticate(token_fn, token):
                    # Clear TCP receive buffer of any pending data
                    request.data
                    # Mimic the response from a normal endpoint
                    # To use the same standards
                    return decorated_self.send_errors(
                        label="Invalid token", message="Received '%s'" % token,
                        headers=headers, code=bad_code)

            # Check roles
            if len(roles) > 0:
                roles_fn = g._custom_auth.verify_roles
                if not self.authenticate_roles(roles_fn, roles):
                    return decorated_self.send_errors(
                        label="Missing privileges",
                        message="One or more role required", code=bad_code)

            return f(*args, **kwargs)

        return decorated


authentication = HTTPTokenAuth()

logger.info(
    "Initizialized a valid authentication class: [%s]"
    % authentication._scheme)
