# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from .... import myself, lic, get_logger

import abc
import jwt
from flask_httpauth import HTTPTokenAuth


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

    def __init__(self, auth_type='Bearer'):
        self.auth = HTTPTokenAuth(auth_type)
        logger.warning(
            "Initizialized a valid authentication class: [%s]" % auth_type)

    def create_token(self, payload):
        byte_token = jwt.encode(
            payload, SECRET, algorithm=self.JWT_ALGO)
        return byte_token

    def parse_token(self, token):
        print("TOKEN IS", token)
        if token is not None:
            import jwt
            payload = jwt.decode(token, SECRET, algorithms=[self.JWT_ALGO])
            print("PAYLOAD", payload)
            # user = g.User.nodes.get(token=token)

    @abc.abstractmethod
    def get_user_object(self, username):
        return

    @abc.abstractmethod
    def fill_payload(self, userobj):
        return

    def make_login(self, username, password):
        user = self.get_user_object(username)
        if not user or not self.check_password(user.hash_password, password):
            return None
        return self.create_token(self.fill_payload(user))
