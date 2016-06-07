# -*- coding: utf-8 -*-

"""
Implement authentication with graphdb as user database

Note: to delete the whole db
MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r
"""

from __future__ import absolute_import
from datetime import datetime
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

    def getUUID(self):
        return "ABC-UUID"
        # return str(uuid.uuid4())

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

    def fill_payload(self, userobj):

        """
# // TO FIX

This method should be custom.
This means it should be implemented inside the vanilla folder,
instead of here
        """

# ADD IRODS USERNAME?
        # print("OBJ", userobj.email)

        return {
            'user_id': userobj.uuid,
            'hpwd': userobj.password,
            'emitted': str(datetime.now())
        }

    def init_users_and_roles(self):

        if not len(self._graph.Role.nodes) > 0:
            logger.warning("No roles inside graphdb. Injected defaults.")
            for role in self.DEFAULT_ROLES:
                role = self._graph.Role(name=role, description="automatic")
                role.save()

        if not len(self._graph.User.nodes) > 0:
            logger.warning("No users inside graphdb. Injected default.")
            user = self._graph.User(
                uuid=self.getUUID(),
                email=self.DEFAULT_USER,
                authmethod='credentials',
                name='Default', surname='User',
                password=self.hash_password(self.DEFAULT_PASSWORD))
            user.save()

            for role in self.DEFAULT_ROLES:
                role_obj = self._graph.Role.nodes.get(name=role)
                user.roles.connect(role_obj)

    def save_token(self, user, token):

        token_node = self._graph.Token()
        token_node.token = token
        token_node.creation = datetime.now()
        token_node.last_access = datetime.now()
        # token_node.expiration = ???

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

    def invalidate_all_tokens(self, user):
        user.uuid = self.getUUID()
        user.save()

    def invalidate_token(self, user, token):
        token.emitted_for.disconnect(user)
