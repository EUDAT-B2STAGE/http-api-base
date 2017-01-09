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
import os
from commons.logs import get_logger
from commons.services.uuid import getUUID
from ....confs.config import USER, PWD, \
    ROLE_ADMIN, ROLE_INTERNAL, ROLE_USER
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

    # This string will be replaced with a proper secret file
    JWT_SECRET = 'top secret!'

    JWT_ALGO = 'HS256'
# TO FIX: already defined in auth.py HTTPAUTH_DEFAULT_SCHEME
    token_type = 'Bearer'
    DEFAULT_USER = USER
    DEFAULT_PASSWORD = PWD
    DEFAULT_ROLE = ROLE_USER
    DEFAULT_ROLES = [ROLE_USER, ROLE_INTERNAL, ROLE_ADMIN]
    _oauth2 = {}
    _payload = {}
    _user = None
    _token = None

    longTTL = 2592000     # 1 month in seconds
    shortTTL = 604800     # 1 week in seconds

    @abc.abstractmethod
    def __init__(self, services=None):
        """
        Make sure you can create an instance/connection,
        or reuse one service from `server.py` operations.
        """
        return

    # ########################
    # # Configure Secret Key #
    # ########################
    def import_secret(self, abs_filename):
        """
        Configure the JWT_SECRET from a file

        If the file does not exist, print instructions
        to create it from a shell with a random key
        and continues with default key
        """
        try:
            self.JWT_SECRET = open(abs_filename, 'rb').read()
        except IOError:
            logger.warning("Jwt secret file not found: %s" % abs_filename)
            logger.warning("You are using a default secret key")
            logger.info("To create your own secret file:")
            # full_path = os.path.dirname(abs_filename)
            # if not os.path.isdir(full_path):
            #     print('mkdir -p {filename}'.format(filename=full_path))
            logger.info("head -c 24 /dev/urandom > %s" % abs_filename)
            # import sys
            # sys.exit(1)

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

    def get_user(self):
        return self._user

    def get_token(self):
        return self._token

    @staticmethod
    def get_host_info():

        import socket

        ###############
        # Note: timeout do not work on dns lookup...
        # also read:
        # http://depier.re/attempts_to_speed_up_gethostbyaddr/

        # # if getting slow when network is unreachable
        # timer = 1
        # if hasattr(socket, 'setdefaulttimeout'):
        #     socket.setdefaulttimeout(timer)
        # # socket.socket.settimeout(timer)

        ###############
        hostname = ""
        from flask import current_app, request
        ip = request.remote_addr

        if current_app.config['TESTING'] and ip is None:
            pass
        else:
            try:
                # note: this will return the ip if hostname is not available
                hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
            except Exception as e:
                logger.warning(
                    "Hostname from '%s' solving:\nerror '%s'" % (ip, e))
        return ip, hostname

    def create_token(self, payload):
        """ Generate a byte token with JWT library to encrypt the payload """
        self._payload = payload
        self._user = self.get_user_object(payload=self._payload)
        encode = jwt.encode(
            payload, self.JWT_SECRET, algorithm=self.JWT_ALGO).decode('ascii')

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

    def unpack_token(self, token):

        payload = None

        try:
            payload = jwt.decode(
                token, self.JWT_SECRET, algorithms=[self.JWT_ALGO])
        # now > exp
        except jwt.exceptions.ExpiredSignatureError as e:
# should this token be invalidated into the DB?
            logger.warning("Unable to decode JWT token. %s" % e)
        # now < nbf
        except jwt.exceptions.ImmatureSignatureError as e:
            logger.warning("Unable to decode JWT token. %s" % e)
        except Exception as e:
            logger.warning("Unable to decode JWT token. %s" % e)

        return payload

    def verify_roles(self, roles):

        current_roles = self.get_roles_from_user()
        for role in roles:
            if role not in current_roles:
                logger.warning("Auth role '%s' missing for request" % role)
                return False
        return True

    def verify_token(self, token):

        # Force token cleaning
        self._payload = {}
        self._user = None

        if token is None:
            return False

        # Decode the current token
        tmp_payload = self.unpack_token(token)
        if tmp_payload is None:
            return False
        else:
            self._payload = tmp_payload

        # Get the user from payload
        self._user = self.get_user_object(payload=self._payload)
        if self._user is None:
            return False

        if not self.verify_token_custom(
           jti=self._payload['jti'], user=self._user, payload=self._payload):
            return False
        # e.g. for graph: verify the (token <- user) link

        if not self.refresh_token(self._payload['jti']):
            return False

        logger.debug("User authorized")
        self._token = token
        return True

    def save_token(self, user, token, jti):
        logger.debug("Token is not saved in base authentication")

    @abc.abstractmethod
    def init_users_and_roles(self):
        """
        Create roles and a user if no one exists.
        A possible algorithm:

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
    def create_user(self, userdata, roles=[DEFAULT_ROLE]):
        """
        A method to create a new user following some standards.
        - The user should be at least associated to the default (basic) role
        - More to come
        """
        return

    @abc.abstractmethod
    def get_roles_from_user(self, userobj=None):
        """
        How to retrieve the role of a user from the current service,
        based on a user object.
        If not provided, uses the current user obj stored in self._user.
        """
        return

    @abc.abstractmethod
    def store_oauth2_user(self, current_user, token):
        """
        Allow external accounts (oauth2 credentials)
        to be connected to internal local user.

        (requires an ExternalAccounts model defined for current service)
        """
        return ('internal_user', 'external_user')

    @abc.abstractmethod
    def store_proxy_cert(self, external_user, proxy):
        """ Save the proxy certificate name into oauth2 account """
        return

    @abc.abstractmethod
    def get_user_object(self, username=None, payload=None):
        """
        How to retrieve the user from the current service,
        based on the unique username given, or from the content of the token
        """
        return

    @abc.abstractmethod
    def get_tokens(self, user=None, token_jti=None):
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
    def invalidate_token(self, token, user=None):
        """
            With this method the specified token must be invalidated
            as expected after a user logout
        """
        return

    @abc.abstractmethod
    def destroy_token(self, token_id):
        """
            Destroy a token by removing all references in DB
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
