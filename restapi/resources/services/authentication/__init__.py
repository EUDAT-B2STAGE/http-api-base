# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import absolute_import
from .... import myself, lic, get_logger

from confs.config import USER, PWD, ROLE_ADMIN, ROLE_USER

import abc
import jwt
import hmac
import hashlib
import base64

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class BaseAuthentication(metaclass=abc.ABCMeta):

    """
    An almost abstract class with methods
    to be implemented with a new service
    that aims to store credentials of users and roles.
    """

    SECRET = 'top secret!'
    JWT_ALGO = 'HS256'
    DEFAULT_USER = USER
    DEFAULT_PASSWORD = PWD
    DEFAULT_ROLES = [ROLE_USER, ROLE_ADMIN]
    _oauth2 = {}

    @abc.abstractmethod
    def __init__(self, services=None):
        """
        Make sure you can create an instance/connection,
        or reuse one service from `server.py` operations.
        """
        return

    def setup_secret(self, secret):
        self.SECRET = secret

    def set_oauth2_services(self, services):
        self._oauth2 = services

    @staticmethod
    def encode_string(string):
        """ Encodes a string to bytes, if it isn't already. """
        if isinstance(string, str):
            string = string.encode('utf-8')
        return string

    @staticmethod
    def hash_password(password):
        """ Original source:
        # https://github.com/mattupstate/flask-security
        #    /blob/develop/flask_security/utils.py#L110
        """

        salt = "Unknown"

        h = hmac.new(
            BaseAuthentication.encode_string(salt),
            BaseAuthentication.encode_string(password),
            hashlib.sha512)
        return base64.b64encode(h.digest()).decode('ascii')

    @staticmethod
    def check_passwords(hashed_password, password):
        proposed_password = BaseAuthentication.hash_password(password)
        return hashed_password == proposed_password

    def create_token(self, payload):
        """ Generate a byte token with JWT library to encrypt the payload """
        return jwt.encode(
            payload, self.SECRET, algorithm=self.JWT_ALGO).decode('ascii')

    def parse_token(self, token):
        payload = {}
        if token is not None:
            try:
                payload = jwt.decode(
                    token, self.SECRET, algorithms=[self.JWT_ALGO])
            except:
                logger.warning("Unable to decode JWT token")
        return payload

    def verify_token(self, token):
        # return False
        # print("TOKEN", token)
        self._payload = payload = self.parse_token(token)
        # print("TOKEN CONTENT", payload)
        self._user = user = self.get_user_object(payload=payload)
        if user is not None:
            logger.info("User authorized")
# // TO FIX
# CHECK TTL?
            return True

        return False

    def save_token(self, user, token):
        logger.debug("Token is not saved in base authentication")

    @abc.abstractmethod
    def init_users_and_roles(self):
        """
        Here i write a possible good pattern:

        if not exist_one_role():
            for role in self.DEFAULT_ROLES:
                create_role(role)
        if not exist_one_user():
            create_user(
                email=self.DEFAULT_USER,
                name="Whatever", surname="YouLike",
                password=self.DEFAULT_PASSWORD,
                roles=DEFAULT_ROLES)
        """
        return

    @abc.abstractmethod
    def get_user_object(self, username=None, payload=None):
        """
        How to retrieve the user from the current service,
        based on the unique username given, or from the content of the token
        """
        return

    @abc.abstractmethod
    def fill_payload(self, userobj):
        """ Informations to store inside the JWT token,
        starting from the user obtained from the current service

from:
http://blog.apcelent.com/json-web-token-tutorial-example-python.html

Following are the claim attributes :

iss: The issuer of the token
sub: The subject of the token
aud: The audience of the token
qsh: query string hash
exp: Token expiration time defined in Unix time
nbf: 'Not before time':
   identifies the time before which the JWT must not be accepted for processing
iat: 'Issued at time', in Unix time, at which the token was issued
jti: JWT ID claim provides a unique identifier for the JWT

        """
        return

    def make_login(self, username, password):
        """ The method which will check if credentials are good to go """

        user = self.get_user_object(username=username)
        if user is None:
            return None

        try:
            # Check if Oauth2 is enabled
            if user.authmethod != 'credentials':
                return None
        except:
            # Missing authmethod as requested for authentication
            logger.critical("Current authentication db models are broken!")
            return None

# // TO FIX:
# maybe payload should be some basic part + custom payload from the developer
        if self.check_passwords(user.password, password):
            return self.create_token(self.fill_payload(user))

        return None
