# -*- coding: utf-8 -*-

"""
Implement authentication with graphdb as user database

Note: to delete the whole db
MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r

Remove tokens:
MATCH (a:Token) WHERE NOT (a)<-[]-() DELETE a

"""

from __future__ import absolute_import
import pytz
from datetime import datetime, timedelta
from commons.services.uuid import getUUID
from commons.logs import get_logger
from . import BaseAuthentication
from ..detect import GRAPHDB_AVAILABLE
from .... import myself, lic

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


if not GRAPHDB_AVAILABLE:
    logger.critical("No GraphDB service found for auth")
    exit(1)


class Authentication(BaseAuthentication):

    def __init__(self, services=None):
        self._graph = services.get('neo4j').get_instance()

    def get_user_object(self, username=None, payload=None):

        user = None
        try:
            if username is not None:
                user = self._graph.User.nodes.get(email=username)
            if payload is not None and 'user_id' in payload:
                user = self._graph.User.nodes.get(uuid=payload['user_id'])
        except self._graph.User.DoesNotExist:
            logger.warning("Could not find user for '%s'" % username)
        return user

    def get_roles_from_user(self, userobj=None):

        roles = []
        if userobj is None:
            try:
                userobj = self._user
            except Exception as e:
                logger.warning("Roles check: invalid current user.\n%s" % e)
                return roles

        for role in userobj.roles.all():
            roles.append(role.name)
        return roles

    def fill_custom_payload(self, userobj, payload):
## // TO FIX
        """
This method should be implemented inside the vanilla folder,
instead of here
        """
        return payload

    def create_user(self, userdata, roles=[]):

        if self.DEFAULT_ROLE not in roles:
            roles.append(self.DEFAULT_ROLE)

        user_node = self._graph.User(**userdata)
        try:
            user_node.save()
        except Exception as e:
            message = "Can't create user %s:\n%s" % (userdata['email'], e)
            logger.error(message)
            raise AttributeError(message)

        # Link the new external account to at least at the very default Role
        for role in roles:
            logger.debug("Adding role %s" % role)
            try:
                role_obj = self._graph.Role.nodes.get(name=role)
            except self._graph.Role.DoesNotExist:
                raise Exception("Graph role %s does not exist" % role)
            user_node.roles.connect(role_obj)

        return user_node

    def create_role(self, role, description="automatic"):
        role = self._graph.Role(name=role, description=description)
        role.save()
        return role

    def init_users_and_roles(self):

        # Handle system roles
        current_roles = []
        current_roles_objs = self._graph.Role.nodes.all()
        for role in current_roles_objs:
            current_roles.append(role.name)

        for role in self.DEFAULT_ROLES:
            if role not in current_roles:
                self.create_role(role)

        from flask import current_app
        if current_app.config['TESTING']:
            # Create some users for testing
            pass

        # Default user (if no users yet available)
        if not len(self._graph.User.nodes) > 0:
            logger.warning("No users inside graphdb. Injecting default.")
            self.create_user({
                'uuid': getUUID(),
                'email': self.DEFAULT_USER,
                'authmethod': 'credentials',
                'name': 'Default', 'surname': 'User',
                'password': self.hash_password(self.DEFAULT_PASSWORD)
            }, roles=self.DEFAULT_ROLES)

    def save_token(self, user, token, jti):

        now = datetime.now(pytz.utc)
        exp = now + timedelta(seconds=self.shortTTL)

        token_node = self._graph.Token()
        token_node.jti = jti
        token_node.token = token
        token_node.creation = now
        token_node.last_access = now
        token_node.expiration = exp

        ip, hostname = self.get_host_info()
        token_node.IP = ip
        token_node.hostname = hostname

        token_node.save()
        token_node.emitted_for.connect(user)

        logger.debug("Token stored in graphDB")

    def verify_token_custom(self, jti, user, payload):
        try:
            token_node = self._graph.Token.nodes.get(jti=jti)
        except self._graph.Token.DoesNotExist:
            return False
        if not token_node.emitted_for.is_connected(user):
            return False

        return True

    def refresh_token(self, jti):
        now = datetime.now(pytz.utc)
        try:
            token_node = self._graph.Token.nodes.get(jti=jti)

            if now > token_node.expiration:
                self.invalidate_token(token=token_node.token)
                logger.critical("This token is not longer valid")
                return False

            exp = now + timedelta(seconds=self.shortTTL)

            token_node.last_access = now
            token_node.expiration = exp

            token_node.save()

            return True
        except self._graph.Token.DoesNotExist:
            logger.warning("Token %s not found" % jti)
            return False

    def get_tokens(self, user=None, token_jti=None):
        # TO FIX: TTL should be considered?

        list = []
        tokens = None

        if user is not None:
            tokens = user.tokens.all()
        elif token_jti is not None:
            try:
                tokens = [self._graph.Token.nodes.get(jti=token_jti)]
            except self._graph.Token.DoesNotExist:
                pass

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
        user.save()

    def invalidate_token(self, user=None, token=None):
        if token is None:
## // TO FIX:
## WARNING: this is a global token across different users!
            token = self._latest_token
        if user is None:
            user = self._user

        try:
            token_node = self._graph.Token.nodes.get(token=token)
            token_node.emitted_for.disconnect(user)
        except self._graph.Token.DoesNotExist:
            logger.warning("Could not invalidate token")

    def destroy_token(self, token_id):
        try:
            token = self._graph.Token.nodes.get(jti=token_id)
            token.delete()
            return True

        except self._graph.Token.DoesNotExist:
            return False

    def save_oauth2_info_to_user(self, graph, current_user, token):
        """
        Allow external accounts (oauth2 credentials)
        to be connected to internal local user
        """

        email = current_user.data.get('email')

        # A graph node for internal accounts associated to oauth2
        try:
            user_node = graph.User.nodes.get(email=email)
            if user_node.authmethod != 'oauth2':
                return {'errors': [{
                    'invalid email':
                    'Account already exists with other credentials'}]}
        except graph.User.DoesNotExist:
## // TO FIX:
# TO BE VERIFIED
            user_node = self.create_user(userdata={
                'uuid': getUUID(),
                'email': email,
                'authmethod': 'oauth2'
            })

        # A graph node for external oauth2 account
        try:
            oauth2_external = graph.ExternalAccounts.nodes.get(username=email)
        except graph.ExternalAccounts.DoesNotExist:
            oauth2_external = graph.ExternalAccounts(username=email)
        oauth2_external.email = current_user.data.get('email')
        oauth2_external.token = token
        oauth2_external.certificate_cn = current_user.data.get('cn')
        oauth2_external.save()

        user_node.externals.connect(oauth2_external)

        return user_node
