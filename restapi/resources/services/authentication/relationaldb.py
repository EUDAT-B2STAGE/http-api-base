# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import absolute_import
import sqlalchemy
# import pytz
from datetime import datetime, timedelta
from commons.services.uuid import getUUID
from ..detect import SQL_AVAILABLE
from . import BaseAuthentication
from .... import myself, lic
from commons.logs import get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

if not SQL_AVAILABLE:
    logger.critical("No SQLalchemy service found for auth")
    exit(1)


class Authentication(BaseAuthentication):

    def __init__(self, services=None):
        """
        SQLalchemy should be created only once.
        I will recover initial instance from the Flask app services.
        """

        self._db = services.get('sql').get_instance()

    def fill_custom_payload(self, userobj, payload):
        """
# // TO FIX

This method should be implemented inside the vanilla folder,
instead of here
        """
        return payload

    def get_user_object(self, username=None, payload=None):
        user = None
        if username is not None:
            user = self._db.User.query.filter_by(email=username).first()
        if payload is not None and 'user_id' in payload:
            user = self._db.User.query.filter_by(
                uuid=payload['user_id']).first()
        return user

###############
## TO FIX
    def get_roles_from_user(self, userobj=None):
        return NotImplementedError("To do")

    def create_user(self, userdata, roles=[]):
        if self.DEFAULT_ROLE not in roles:
            roles.append(self.DEFAULT_ROLE)
        return NotImplementedError("To do")
## TO FIX
###############

    def init_users_and_roles(self):

        missing_role = missing_user = False

        try:
            # if no roles
            missing_role = not self._db.Role.query.first()
            if missing_role:
                logger.warning("No roles inside db. Injected defaults.")
                for role in self.DEFAULT_ROLES:
                    sqlrole = self._db.Role(name=role, description="automatic")
                    self._db.session.add(sqlrole)

            # if no users
            missing_user = not self._db.User.query.first()
            if missing_user:
                logger.warning("No users inside db. Injected default.")
                user = self._db.User(
                    uuid=getUUID(),
                    email=self.DEFAULT_USER,
                    authmethod='credentials',
                    name='Default', surname='User',
                    password=self.hash_password(self.DEFAULT_PASSWORD))

                # link roles into users
                for role in self.DEFAULT_ROLES:
                    sqlrole = self._db.Role.query.filter_by(name=role).first()
                    user.roles.append(sqlrole)
                self._db.session.add(user)

        except sqlalchemy.exc.OperationalError:
            raise AttributeError("Existing SQL tables are not consistent " +
                                 "to existing models. Please consider " +
                                 "rebuilding your DB.")

        if missing_user or missing_role:
            self._db.session.commit()

    def save_token(self, user, token, jti):

        from flask import request
        import socket
        ip = request.remote_addr
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
        except Exception:
            hostname = ""

        now = datetime.now()
        exp = now + timedelta(seconds=self.shortTTL)

        token_entry = self._db.Token(
            jti=jti,
            token=token,
            creation=now,
            last_access=now,
            expiration=exp,
            IP=ip,
            hostname=hostname
        )

        token_entry.emitted_for = user

        self._db.session.add(token_entry)
        self._db.session.commit()

        logger.debug("Token stored in graphDB")

    def refresh_token(self, jti):
        now = datetime.now()
        token_entry = self._db.Token.query.filter_by(jti=jti).first()
        if token_entry is None:
            return False

        if now > token_entry.expiration:
            self.invalidate_token(token=token_entry.token)
            logger.critical("This token is no longer valid")
            return False

        exp = now + timedelta(seconds=self.shortTTL)

        token_entry.last_access = now
        token_entry.expiration = exp

        self._db.session.add(token_entry)
        self._db.session.commit()

        return True

    def get_tokens(self, user=None, token_jti=None):
        # TO FIX: TTL should be considered?

        list = []
        tokens = None

        if user is not None:
            tokens = user.tokens.all()
        elif token_jti is not None:
            tokens = [self._db.Token.query.filter_by(jti=token_jti).first()]

        if tokens is not None:
            for token in tokens:

                t = {}

                t["id"] = token.jti
                t["token"] = token.token
                t["emitted"] = token.creation.strftime('%s')
                t["last_access"] = token.last_access.strftime('%s')
                if token.expiration is not None:
                    t["expiration"] = token.expiration.strftime('%s')
                t["IP"] = token.IP
                t["hostname"] = token.hostname
                list.append(t)

        return list

    def invalidate_all_tokens(self, user=None):
        if user is None:
            user = self._user

        user.uuid = getUUID()
        self._db.session.add(user)
        self._db.session.commit()

    def invalidate_token(self, user=None, token=None):
        if token is None:
## // TO FIX:
## WARNING: this is a global token across different users!
            token = self._latest_token
        if user is None:
            user = self._user

        token_entry = self._db.Token.query.filter_by(token=token).first()
        if token_entry is not None:
            token_entry.emitted_for = None
            self._db.session.commit()
        else:
            logger.warning("Could not invalidate token")

    def destroy_token(self, token_id):
        token = self._db.Token.query.filter_by(jti=token_id).first()

        if token is None:
            return False

        token.emitted_for = None    # required?
        self._db.session.delete(token)
        self._db.session.commit()
        return True

    def store_oauth2_user(self, current_user, token):
        """
        Allow external accounts (oauth2 credentials)
        to be connected to internal local user
        """

        email = current_user.data.get('email')
        cn = current_user.data.get('cn')

        # Check if a user already exists with this email
        internal_user = None
        internal_users = self._db.User.query.filter(
            self._db.User.email == email).all()

        # If something found
        if len(internal_users) > 0:
            # Should never happen, please
            if len(internal_users) > 1:
                return None
            internal_user = internal_users.pop()
            logger.debug("Existing internal user %s" % internal_user)
            # A user already locally exists with another authmethod. Not good.
            if internal_user.authmethod != 'oauth2':
                return None
        # If missing, add it locally
        else:
            # Create new one
            internal_user = self._db.User(
                uuid=getUUID(), email=email, authmethod='oauth2')
            # link default role into users
            internal_user.roles.append(
                self._db.Role.query.filter_by(name=self.DEFAULT_ROLE).first())
            self._db.session.add(internal_user)
            self._db.session.commit()
            logger.info("Created internal user %s" % internal_user)

        # Get ExternalAccount for the oauth2 data if exists
        external_user = self._db.ExternalAccounts \
            .query.filter_by(username=email).first()
        # or create it otherwise
        if external_user is None:
            external_user = self._db.ExternalAccounts(username=email)

            # Connect the external account to the current user
            external_user.main_user = internal_user
            # Note: for pre-production release
            # we allow only one external account per local user
            logger.info("Created external user %s" % external_user)

        # Update external user data to latest info received
        external_user.email = email
        external_user.token = token
        external_user.certificate_cn = cn

        self._db.session.add(external_user)
        self._db.session.commit()
        logger.debug("Updated external user %s" % external_user)

        return internal_user, external_user

    def store_proxy_cert(self, external_user, proxy):
        if external_user is None:
            return False
        external_user.proxyfile = proxy
## // TO FIX
## Convert into dedicated method?
        self._db.session.add(external_user)
        self._db.session.commit()
        return True

## // TO FIX
## make this abstract for graphdb too?
    def oauth_from_token(self, token):

        extus = self._db.ExternalAccounts.query.filter_by(token=token).first()
        intus = extus.main_user
        # print(token, intus, extus)
        return intus, extus
