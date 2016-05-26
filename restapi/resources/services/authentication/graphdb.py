# -*- coding: utf-8 -*-

"""
Implement authentication with graphdb as user database

Note: to delete the whole db
MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r
"""

from __future__ import absolute_import

from datetime import datetime
from .generic import BaseAuthentication
from ..neo4j.graph import GraphFarm

from .... import get_logger
logger = get_logger(__name__)


class Authentication(BaseAuthentication):

    def __init__(self):
        self._graph = GraphFarm().get_graph_instance()

    def get_user_object(self, username=None, payload=None):

        user = None
        self._graph = GraphFarm().get_graph_instance()
        try:
            if username is not None:
                user = self._graph.User.nodes.get(email=username)
            if payload is not None and 'user_id' in payload:
                # Get a neomodel node from id?
                # Workaround from:
                # https://github.com/robinedwards/neomodel/issues/199
                user = self._graph.User(_id=payload['user_id'])
                user.refresh()
        except self._graph.User.DoesNotExist:
            logger.warning("Could not find user for '%s'" % username)
        return user

    def fill_payload(self, userobj):
# // TO FIX
        return {
            'user_id': userobj._id,
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
                email=self.DEFAULT_USER,
                name='Default', surname='User',
                password=self.hash_password(self.DEFAULT_PASSWORD))
            user.save()

            for role in self.DEFAULT_ROLES:
                role_obj = self._graph.Role.nodes.get(name=role)
                user.roles.connect(role_obj)
