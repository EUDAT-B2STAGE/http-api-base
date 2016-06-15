# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import absolute_import
import abc
import jwt
import hmac
import hashlib
import base64
import pytz
from commons.logs import get_logger
from commons.services.uuid import getUUID
from confs.config import USER, PWD, ROLE_ADMIN, ROLE_USER
from datetime import datetime, timedelta
from .... import myself, lic

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
#TO FIX: already defined in auth.py HTTPAUTH_DEFAULT_SCHEME
    token_type = 'Bearer'
    DEFAULT_USER = USER
    DEFAULT_PASSWORD = PWD
    DEFAULT_ROLES = [ROLE_USER, ROLE_ADMIN]
    _oauth2 = {}
    _latest_token = None
    _payload = {}
    _user = None

#TO FIX: to be lengthen. Now are short for testing purpose
    longTTL = 86400     # 1 day in seconds
    shortTTL = 3600     # 1 hour in seconds

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
        self._payload = payload
        self._user = self.get_user_object(payload=self._payload)
        encode = jwt.encode(
            payload, self.SECRET, algorithm=self.JWT_ALGO).decode('ascii')

        return encode, self._payload['jti']

    def verify_token_custom(self, jti, user, payload):
        """
            This method can be implemented by specific Authentication Methods
            to add more specific validation contraints
        """
        return True

    @abc.abstractmethod
    def refresh_token(self, jti):
        """
            Verify shortTTL to refresh token if not expired
            Invalidate token otherwise
        """
        return

    def verify_token(self, token):

        # Force token cleaning
        self._payload = {}
        self._user = None

        if token is None:
            return False

        try:
            self._payload = jwt.decode(
                token, self.SECRET, algorithms=[self.JWT_ALGO])
        # now > exp
        except jwt.exceptions.ExpiredSignatureError as e:
            logger.warning("Unable to decode JWT token. %s" % e)
            # this token should be invalidated into the DB?
            return False
        # now < nbf
        except jwt.exceptions.ImmatureSignatureError as e:
            logger.warning("Unable to decode JWT token. %s" % e)
            return False
        except Exception as e:
            logger.warning("Unable to decode JWT token. %s" % e)
            return False

        self._user = self.get_user_object(payload=self._payload)
        if self._user is None:
            return False

        if not self.verify_token_custom(
           jti=self._payload['jti'], user=self._user, payload=self._payload):
            return False
        # e.g. for graph: verify the (token <- user) link

        if not self.refresh_token(self._payload['jti']):
            return False

        logger.info("User authorized")
        return True

    def save_token(self, user, token, jti):
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
    def list_all_tokens(self, user):
        """
            Return the list of all active tokens
        """
        return

    @abc.abstractmethod
    def invalidate_all_tokens(self, user=None):
        """
            With this method all token emitted for this user must be
            invalidated (no longer valid starting from now)
        """
        return

    @abc.abstractmethod
    def invalidate_token(self, user=None, token=None):
        """
            With this method the specified token must be invalidated
            as expected after a user logout
        """
        return

    def fill_custom_payload(self, userobj, payload):
        """
            This method can be implemented by specific Authentication Methods
            to add more specific payload content
        """
        return payload

    def fill_payload(self, userobj):
        """ Informations to store inside the JWT token,
        starting from the user obtained from the current service

        Claim attributes listed here:
        http://blog.apcelent.com/json-web-token-tutorial-example-python.html

        TTL is measured in seconds
        """

        now = datetime.now(pytz.utc)
        nbf = now   # you can add a timedelta
        exp = now + timedelta(seconds=self.longTTL)

        payload = {
            'user_id': userobj.uuid,
            'hpwd': userobj.password,
            'iat': now,
            'nbf': nbf,
            'exp': exp,
            'jti': getUUID()
        }

        return self.fill_custom_payload(userobj, payload)

    def make_login(self, username, password):
        """ The method which will check if credentials are good to go """

        user = self.get_user_object(username=username)
        if user is None:
            return None, None

        try:
            # Check if Oauth2 is enabled
            if user.authmethod != 'credentials':
                return None, None
        except:
            # Missing authmethod as requested for authentication
            logger.critical("Current authentication db models are broken!")
            return None, None

# // TO FIX:
# maybe payload should be some basic part + custom payload from the developer
        if self.check_passwords(user.password, password):
            return self.create_token(self.fill_payload(user))

        return None, None
