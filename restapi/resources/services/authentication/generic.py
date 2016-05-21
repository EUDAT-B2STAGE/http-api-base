# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from .... import myself, lic, get_logger

import jwt
from flask_httpauth import HTTPTokenAuth


__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

SECRET = 'top secret!'


class BaseAuthentication(object):

    """
    An almost abstract class with methods
    to be implemented with a new service
    that aims to store credentials of users and roles.
    """

    JWT_ALGO = 'HS256'

    def __init__(self, auth_type='Bearer'):
        self.auth = HTTPTokenAuth(auth_type)
        logger.critical("Work in progress")

    def create_token(self, payload):
        byte_token = jwt.encode(
            payload, SECRET, algorithm=self.JWT_ALGO)
        return byte_token
