# -*- coding: utf-8 -*-

from __future__ import division, absolute_import

from commons import htmlcodes as hcodes
from functools import wraps
from flask import request
from werkzeug.datastructures import Authorization
from . import myself, lic
from commons.logs import get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

# Few costants
HTTPAUTH_DEFAULT_SCHEME = "Bearer"

"""
The tokens used are RFC6750 Bearer tokens.

The Resource should validate the tokens using the token validation endpoint;
its basic use is by adding
'Authorization: Bearer ' + tokenString to the HTTP header;
cf. RFC6749 section 7.1.

Note that anyone can validate a token as it is a bearer token:
there is no client id nor is client authentication required.
"""

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
        self.verify_token_callback = None
        self.verify_roles_callback = None

    def authenticate_header(self):
        return '{0} realm="{1}"'.format(self._scheme, self._realm)

    def callbacks(self, verify_token_f=None, verify_roles_f=None):
        self.verify_token_callback = verify_token_f
        self.verify_roles_callback = verify_roles_f

    def authenticate(self, auth, stored_password):
        if auth:
            token = auth[HTTPAUTH_TOKEN_KEY]
        else:
            token = ""
        if self.verify_token_callback:
            return self.verify_token_callback(token)
        return False

    @staticmethod
    def get_authentication_from_headers():
        """
        Returns (auth, token)
        """
        return request.headers.get(HTTPAUTH_AUTH_FIELD).split(None, 1)

    def authenticate_roles(self, roles):
        if self.verify_roles_callback:
            return self.verify_roles_callback(roles)
        return False

    def roles_required(self, *roles):
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):

                # Call the internal api method by getting 'self'
                try:
                    decorated_self = list(args).pop(0)
                except AttributeError:
                    decorated_self = None

                if not self.authenticate_roles(roles):
                    return decorated_self.force_response(
                        errors={"Missing privileges":
                                "One or more role required"},
                        code=hcodes.HTTP_BAD_UNAUTHORIZED
                    )
                return f(*args, **kwargs)
            return decorated
        return decorator

    def login_required(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = "EMPTY"

            auth = request.authorization
            if auth is None and HTTPAUTH_AUTH_FIELD in request.headers:
                # Flask/Werkzeug do not recognize any authentication types
                # other than Basic or Digest, so here we parse the header by
                # hand
                try:
                    auth_type, token = self.get_authentication_from_headers()
                    auth = \
                        Authorization(auth_type, {HTTPAUTH_TOKEN_KEY: token})
                except ValueError:
                    # The Authorization header is either empty or has no token
                    pass

            # Call the internal api method by getting 'self'
            try:
                decorated_self = list(args).pop(0)
            except AttributeError:
                decorated_self = None

            # if the auth type does not match, we act as if there is no auth
            # this is better than failing directly, as it allows the callback
            # to handle special cases, like supporting multiple auth types
            if auth is not None and auth.type.lower() != self._scheme.lower():
                auth = None

            # Flask normally handles OPTIONS requests on its own, but in the
            # case it is configured to forward those to the application, we
            # need to ignore authentication headers and let the request through
            # to avoid unwanted interactions with CORS.
            if request.method != 'OPTIONS':  # pragma: no cover
                if auth and auth.username:
                    password = self.get_password_callback(auth.username)
                else:
                    password = None
                if not self.authenticate(auth, password):
                    # Clear TCP receive buffer of any pending data
                    request.data
                    headers = {
                        HTTPAUTH_AUTH_HEADER: self.authenticate_header()}

                    # Mimic the response from a normal endpoint
                    # To use the same standards
                    return decorated_self.force_response(
                        errors={"Invalid token": "Received '%s'" % token},
                        headers=headers,
                        code=hcodes.HTTP_BAD_UNAUTHORIZED
                    )

            # Save token
            if decorated_self is not None:
                decorated_self.set_latest_token(token)

            return f(*args, **kwargs)
        return decorated


auth = HTTPTokenAuth()
logger.info(
    "Initizialized a valid authentication class: [%s]" % auth._scheme)
