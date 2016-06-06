# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import absolute_import

from datetime import datetime
from .... import myself, lic, get_logger
from .generic import BaseAuthentication
from ..sql.alchemy import SQLFarm

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


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
        print("USER", user)
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
