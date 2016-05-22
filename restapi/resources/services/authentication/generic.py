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
print("MUST USE AUTH", auth)


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

    def create_token(self, payload):
        """ Generate a byte token with JWT library to encrypt the payload """
        return jwt.encode(payload, SECRET, algorithm=self.JWT_ALGO)

    def parse_token(self, token):
        payload = {}
        print("TOKEN IS", token)
        if token is not None:
            import jwt
            payload = jwt.decode(token, SECRET, algorithms=[self.JWT_ALGO])
            print("PAYLOAD", payload)
            # user = g.User.nodes.get(token=token)
        return payload

    @abc.abstractmethod
    def init_users_and_roles(self):
        """
        Here is a possible good pattern:

        if not exist_one_role:
            for role in self.DEFAULT_ROLES:
                create_role(role)
        if not exist_one_user:
            create_user(
                email=self.DEFAULT_USER,
                name="Whatever", surname="YouLike",
                password=self.DEFAULT_PASSWORD,
                roles=DEFAULT_ROLES)
        """
        return

    @abc.abstractmethod
    def get_user_object(self, username):
        return

    @abc.abstractmethod
    def fill_payload(self, userobj):
        return

    def make_login(self, username, password):
        token = None
        print("\n\n\nMAKE THIS WORK\n\n\n", username, password, "\n\n")
        user = self.get_user_object(username)
        if user and self.check_password(user.hash_password, password):
            token = self.create_token(self.fill_payload(user))
        return token
