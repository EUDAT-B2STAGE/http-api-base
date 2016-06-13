# -*- coding: utf-8 -*-

"""
Implement authentication with graphdb as user database

Note: to delete the whole db
MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r
"""

from __future__ import absolute_import
import pytz
from datetime import datetime, timedelta
from commons.services.uuid import getUUID
from . import BaseAuthentication
from ..detect import GRAPHDB_AVAILABLE
from .... import myself, lic, get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


if not GRAPHDB_AVAILABLE:
    logger.critical("No GraphDB service found for auth")
    exit(1)


class Authentication(BaseAuthentication):

    def __init__(self, services=None):
        self._graph = services.get('neo4j')().get_instance()

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

    def fill_custom_payload(self, userobj, payload):
        """
# // TO FIX

This method should be implemented inside the vanilla folder,
instead of here
        """
        return payload

    def init_users_and_roles(self):

        if not len(self._graph.Role.nodes) > 0:
            logger.warning("No roles inside graphdb. Injected defaults.")
            for role in self.DEFAULT_ROLES:
                role = self._graph.Role(name=role, description="automatic")
                role.save()

        if not len(self._graph.User.nodes) > 0:
            logger.warning("No users inside graphdb. Injected default.")
            user = self._graph.User(
                uuid=getUUID(),
                email=self.DEFAULT_USER,
                authmethod='credentials',
                name='Default', surname='User',
                password=self.hash_password(self.DEFAULT_PASSWORD))
            user.save()

            for role in self.DEFAULT_ROLES:
                role_obj = self._graph.Role.nodes.get(name=role)
                user.roles.connect(role_obj)

    def save_token(self, user, token, jti):

        now = datetime.now(pytz.utc)
        exp = now + timedelta(seconds=self.shortTTL)

        token_node = self._graph.Token()
        token_node.jti = jti
        token_node.token = token
        token_node.creation = now
        token_node.last_access = now
        token_node.expiration = exp
        from flask import request
        import socket
        ip = request.remote_addr
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
        except Exception:
            hostname = ""

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

    def list_all_tokens(self, user):
        # TO FIX: TTL should be considered?

        tokens = user.tokens.all()
        list = []
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
            token = self._latest_token
        if user is None:
            user = self._user

        token_node = self._graph.Token.nodes.get(token=token)
        if token_node is not None:
            token_node.emitted_for.disconnect(user)
        else:
            logger.warning("Could not invalidate token")

    def save_oauth2_info_to_user(self, graph, current_user, token):
        """
        From B2ACCESS endpoint user info,
        update our authentication models
        """

        print("CURRENT USER", current_user.__dict__)
        email = current_user.data.get('email')

        # A graph node for internal accounts associated to oauth2
        try:
            user_node = graph.User.nodes.get(email=email)
            if user_node.authmethod != 'b2access_oauth2':
                return {'errors': [{
                    'invalid email':
                    'Account already exists with other credentials'}]}
        except graph.User.DoesNotExist:
            user_node = graph.User(
                uuid=getUUID(),
                email=email,
                authmethod='b2access_oauth2')

        # A graph node for external oauth2 account
        try:
            b2access_node = graph.ExternalAccounts.nodes.get(
                username=email)
        except graph.ExternalAccounts.DoesNotExist:
            b2access_node = graph.ExternalAccounts(
                username=email)

        b2access_node.email = current_user.data.get('email')
        b2access_node.token = token
        b2access_node.certificate_cn = current_user.data.get('cn')

        b2access_node.save()
        user_node.save()
        user_node.externals.connect(b2access_node)

        return user_node
