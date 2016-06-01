# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import absolute_import
from .... import myself, lic, get_logger
from confs import config
from .generic import BaseAuthentication

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class Authentication(BaseAuthentication):

    def fill_payload(self):
        raise NotImplementedError("SQL authentication to be done")

    def get_user_object(self):
        raise NotImplementedError("SQL authentication to be done")

    def init_users_and_roles(self):
        raise NotImplementedError("SQL authentication to be done")


# ####################################
# # DB init for security
# # THIS WORKS ONLY WITH SQLALCHEMY and flask security
# def db_auth():
#     """ What to do if the main auth object has no rows """

#     missing_role = not Role.query.first()
#     logger.debug("Missing role")
#     if missing_role:
#         udstore.create_role(name=config.ROLE_ADMIN, description='King')
#         udstore.create_role(name=config.ROLE_USER, description='Citizen')
#         logger.debug("Created roles")

#     missing_user = not User.query.first()
#     logger.debug("Missing user")
#     if missing_user:
#         import datetime
#         now = datetime.datetime.utcnow()
#         from flask.ext.security.utils import encrypt_password
#         udstore.create_user(first_name='TheOnlyUser', last_name='IAm',
#                             email=config.USER, confirmed_at=now,
#                             password=encrypt_password(config.PWD))
#         udstore.add_role_to_user(config.USER, config.ROLE_ADMIN)
#         logger.debug("Created user")

#     if missing_user or missing_role:
#         db.session.commit()
#         logger.info("Database init with user/roles from conf")
