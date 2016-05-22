# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from .... import myself, lic, get_logger
from ....auth import auth
from confs.config import USER, PWD, ROLE_ADMIN, ROLE_USER

import abc
import jwt

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

SECRET = 'top secret!'


class BaseAuthentication(metaclass=abc.ABCMeta):

    """
    An almost abstract class with methods
    to be implemented with a new service
    that aims to store credentials of users and roles.
    """

    JWT_ALGO = 'HS256'
    DEFAULT_USER = USER
    DEFAULT_PASSWORD = PWD
    DEFAULT_ROLES = [ROLE_USER, ROLE_ADMIN]

    @staticmethod
    def encode_string(string):
        """ Encodes a string to bytes, if it isn't already. """
        if isinstance(string, str):
            string = string.encode('utf-8')
        return string

    @staticmethod
    def hash_password(password):
        import hmac
        import hashlib
        import base64

        salt = "Unknown"

# https://github.com/mattupstate/flask-security/blob/develop/flask_security/utils.py#L110
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
        return \
            jwt.encode(payload, SECRET, algorithm=self.JWT_ALGO) \
            .decode('ascii')

    def parse_token(self, token):
        payload = {}
        if token is not None:
            try:
                payload = jwt.decode(token, SECRET, algorithms=[self.JWT_ALGO])
            except:
                logger.warning("Unable to decode JWT token")
        return payload

    def verify_token(self, token):
        payload = self.parse_token(token)
        user = self.get_user_object(payload=payload)
        if user is not None:
# // TO FIX:
# Store this object (user) somewhere now?
            print("Obtained user")
            return True
        return False

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
        starting from the user obtained from the current service """
        return

    def make_login(self, username, password):
        """ The method which will check if credentials are good to go """
        token = None
        user = self.get_user_object(username=username)
        if user and self.check_passwords(
           user.password, password):
            token = self.create_token(self.fill_payload(user))
        return token
