# -*- coding: utf-8 -*-

"""
SQL Alchemy:
sqllite, MySQL or Postgres
"""

from __future__ import absolute_import
from commons.databases import DBinstance

# Flask Sqlalchemy needs to have models defined on existing instance
from commons.models import relational as sql
from commons.meta import Meta
from .... import get_logger

logger = get_logger(__name__)


class SQLFarm(DBinstance):

    _db = None

    def init_connection(self, app):
        self.get_instance()
        self._db.init_app(app)
        logger.debug(
            "App attached to '%s'" % app.config.get('SQLALCHEMY_DATABASE_URI'))
        # Create database and tables if they don't exist yet
        with app.app_context():
            self._db.create_all()

    def get_instance(self):
        if self._db is None:
            # LOAD MODELS
            for name, model in Meta().get_classes_from_module(sql).items():
                logger.debug("Loading SQL model '%s'" % name)
                setattr(sql.db, name, model)
            # Save the reference
            self._db = sql.db
            logger.debug("SQLAlchemy for Flask initialized")
        return self._db
