# -*- coding: utf-8 -*-

"""
Sql handling authentication process
"""

from __future__ import absolute_import
import sqlalchemy
# import pytz
from datetime import datetime, timedelta
from rapydo.utils.uuid import getUUID
from rapydo.services.detect import SQL_AVAILABLE
from rapydo.services.authentication import BaseAuthentication
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

if not SQL_AVAILABLE:
    log.critical("No SQLalchemy service found for auth")
    exit(1)


class Authentication(BaseAuthentication):

    def __init__(self, services=None):
        """
        SQLalchemy should be created only once.
        I will recover initial instance from the Flask app services.
        """

        self.myinit()
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

    def get_roles_from_user(self, userobj=None):

        roles = []
        if userobj is None:
            try:
                userobj = self.get_user()
            except Exception as e:
                log.warning("Roles check: invalid current user.\n%s" % e)
                return roles

        for role in userobj.roles:
            roles.append(role.name)
        return roles

    # def create_user(self, userdata, roles=[]):
    # """ UNUSED, should be removed """
    #     if self.default_role not in roles:
    #         roles.append(self.default_role)
    #     return NotImplementedError("To do")

    def init_users_and_roles(self):

        missing_role = missing_user = False

        try:
            # if no roles
            missing_role = not self._db.Role.query.first()
            if missing_role:
                log.warning("No roles inside db. Injected defaults.")
                for role in self.default_roles:
                    sqlrole = self._db.Role(name=role, description="automatic")
                    self._db.session.add(sqlrole)

            # if no users
            missing_user = not self._db.User.query.first()
            if missing_user:
                log.warning("No users inside db. Injected default.")
                user = self._db.User(
                    uuid=getUUID(),
                    email=self.default_user,
                    authmethod='credentials',
                    name='Default', surname='User',
                    password=self.hash_password(self.default_password))

                # link roles into users
                for role in self.default_roles:
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

        # TO FIX: generate a token that never expires for admin tests
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

        log.debug("Token stored inside the DB")

    def refresh_token(self, jti):
        now = datetime.now()
        token_entry = self._db.Token.query.filter_by(jti=jti).first()
        if token_entry is None:
            return False

        if now > token_entry.expiration:
            self.invalidate_token(token=token_entry.token)
            log.critical("This token is no longer valid")
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
        """
            To invalidate all tokens the user uuid is changed
        """
        if user is None:
            user = self._user
        user.uuid = getUUID()
        self._db.session.add(user)
        self._db.session.commit()
        log.warning("User uuid changed to: %s" % user.uuid)
        return True

    def invalidate_token(self, token, user=None):
        if user is None:
            user = self.get_user()

        token_entry = self._db.Token.query.filter_by(token=token).first()
        if token_entry is not None:
            token_entry.emitted_for = None
            self._db.session.commit()
        else:
            log.warning("Could not invalidate token")

        return True

    def verify_token_custom(self, jti, user, payload):
        token_entry = self._db.Token.query.filter_by(jti=jti).first()
        if token_entry is None:
            return False
        if token_entry.emitted_for is None or token_entry.emitted_for != user:
            return False

        return True

    def store_oauth2_user(self, current_user, token):
        """
        Allow external accounts (oauth2 credentials)
        to be connected to internal local user
        """

        try:
            values = current_user.data
        except:
            return None, "Authorized response is invalid"

        # print("TEST", values, type(values))
        if not isinstance(values, dict) or len(values) < 1:
            return None, "Authorized response is empty"

        email = values.get('email')
        cn = values.get('cn')
        ui = values.get('unity:persistent')

        # DN very strange: the current key is something like 'urn:oid:2.5.4.49'
        # is it going to change?
        dn = None
        for key, value in values.items():
            if 'urn:oid' in key:
                dn = values.get(key)
        if dn is None:
            return None, "Missing DN from authorized response..."

        # Check if a user already exists with this email
        internal_user = None
        internal_users = self._db.User.query.filter(
            self._db.User.email == email).all()

        # If something found
        if len(internal_users) > 0:
            # Should never happen, please
            if len(internal_users) > 1:
                log.critical("Multiple users?")
                return None, "Server misconfiguration"
            internal_user = internal_users.pop()
            log.debug("Existing internal user: %s" % internal_user)
            # A user already locally exists with another authmethod. Not good.
            if internal_user.authmethod != 'oauth2':
                return None, "Creating a user which locally already exists"
        # If missing, add it locally
        else:
            # Create new one
            internal_user = self._db.User(
                uuid=getUUID(), email=email, authmethod='oauth2')
            # link default role into users
            internal_user.roles.append(
                self._db.Role.query.filter_by(name=self.default_role).first())
            self._db.session.add(internal_user)
            self._db.session.commit()
            log.info("Created internal user %s" % internal_user)

        # Get ExternalAccount for the oauth2 data if exists
        external_user = self._db.ExternalAccounts \
            .query.filter_by(username=email).first()
        # or create it otherwise
        if external_user is None:
            external_user = self._db.ExternalAccounts(username=email, unity=ui)

            # Connect the external account to the current user
            external_user.main_user = internal_user
            # Note: for pre-production release
            # we allow only one external account per local user
            log.info("Created external user %s" % external_user)

        # Update external user data to latest info received
        external_user.email = email
        external_user.token = token
        external_user.certificate_cn = cn
        external_user.certificate_dn = dn

        self._db.session.add(external_user)
        self._db.session.commit()
        log.debug("Updated external user %s" % external_user)

        return internal_user, external_user

    def store_proxy_cert(self, external_user, proxy):
        if external_user is None:
            return False
        external_user.proxyfile = proxy
        self._db.session.add(external_user)  # can be commented
        self._db.session.commit()
        return True

# TO FIX: make this methods below abstract for graph and others too?

    def oauth_from_token(self, token):
        extus = self._db.ExternalAccounts.query.filter_by(token=token).first()
        intus = extus.main_user
        # print(token, intus, extus)
        return intus, extus

    def associate_object_to_attr(self, obj, key, value):
        setattr(obj, key, value)
        self._db.session.commit()
        return

    # TO FIX: to be cached
    def oauth_from_local(self, internal_user):
        accounts = self._db.ExternalAccounts
        external_user = accounts.query.filter(
            accounts.main_user.has(id=internal_user.id)).first()
        return internal_user, external_user
