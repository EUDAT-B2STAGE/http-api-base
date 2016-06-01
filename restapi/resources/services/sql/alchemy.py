# -*- coding: utf-8 -*-

"""
SQL Alchemy:
sqllite, MySQL or Postgres
"""

from __future__ import absolute_import

from flask.ext.sqlalchemy import SQLAlchemy
from commons.databases import DBinstance
from .... import get_logger
logger = get_logger(__name__)


class SQLFarm(DBinstance):

    def init_connection(self):
        self.get_instance()

    def get_instance(self):

        self._db = SQLAlchemy()
        logger.debug("SQLAlchemy for Flask initialized")
        return self._db
