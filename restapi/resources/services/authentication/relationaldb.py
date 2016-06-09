# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import absolute_import
from datetime import datetime
from ..detect import SQL_AVAILABLE
from . import BaseAuthentication
from .... import myself, lic, get_logger

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

        self._db = services.get('sql')().get_instance()

    def fill_payload(self, userobj):
        print("OBJ", userobj.email)

        return {
            'user_id': userobj.id,
            'hpwd': userobj.password,
            'emitted': str(datetime.now())
        }

    def get_user_object(self, username=None, payload=None):
        user = None
        if username is not None:
            user = self._db.User.query.filter_by(email=username).first()
        if payload is not None and 'user_id' in payload:
            user = self._db.User.query.get(payload['user_id'])
        return user

    def init_users_and_roles(self):

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
                email=self.DEFAULT_USER,
                authmethod='credentials',
                name='Default', surname='User',
                password=self.hash_password(self.DEFAULT_PASSWORD))

            # link roles into users
            for role in self.DEFAULT_ROLES:
                sqlrole = self._db.Role.query.filter_by(name=role).first()
                user.roles.append(sqlrole)
            self._db.session.add(user)

        if missing_user or missing_role:
            self._db.session.commit()

    def list_all_tokens(self, user):
        # TO FIX: TTL should be considered?

        list = []
        list.append(self._db.getUUID())
        """
        tokens = user.tokens.all()
        for token in tokens:
            t = {}

            t["id"] = token._id
            t["token"] = token.token
            t["emitted"] = token.creation.strftime('%s')
            t["last_access"] = token.last_access.strftime('%s')
            if token.expiration is not None:
                t["expiration"] = token.expiration.strftime('%s')
            t["IP"] = token.IP
            t["hostname"] = token.hostname
            list.append(t)
        """
        return list

    def invalidate_all_tokens(self, user=None):
        if user is None:
            user = self._user

        """
        user.uuid = self.getUUID()
        user.save()
        """

    def invalidate_token(self, user=None, token=None):
        if token is None:
            token = self._latest_token
        if user is None:
            user = self._user
        """
        token_node = self._graph.Token.nodes.get(token=token)
        if token_node is not None:
            token_node.emitted_for.disconnect(user)
        else:
            logger.warning("Could not invalidate token")
        """
