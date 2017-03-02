# -*- coding: utf-8 -*-

"""
SQL Alchemy:
sqllite, MySQL or Postgres
"""

from __future__ import absolute_import

import os
from rapydo.utils.services import ServiceFarm
from rapydo.utils.logs import get_logger
from rapydo.core.services.detect import SQL_PROD_AVAILABLE

log = get_logger(__name__)


class SQLFarm(ServiceFarm):
    """

    Creating the farm for SQLalchemy as an API service.

    NOTE: Flask Sqlalchemy needs to have models defined on existing instance;
    for this reason we create the sql instance where models are defined.
    """

    _db = None

    @staticmethod
    def define_service_name():
        return 'sql'

    def init_connection(self, app):

        if SQL_PROD_AVAILABLE:
            prefix = "SQLDB_"

            HOST = os.environ.get(prefix + 'NAME').split('/').pop()
            PORT = os.environ.get(prefix + 'PORT').split(':').pop()
            USER = os.environ.get(prefix + 'ENV_POSTGRES_USER')
            PW = os.environ.get(prefix + 'ENV_POSTGRES_PASSWORD')
            DB = 'SQL_API'

            # dialect+driver://username:password@host:port/database
            # postgresql://scott:tiger@localhost/mydatabase
            link = 'postgresql://%s:%s@%s:%s/%s' % (USER, PW, HOST, PORT, DB)
            app.config['SQLALCHEMY_DATABASE_URI'] = link
            log.info("Production database located")

        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        self.get_instance()

        # # Create the sqllite file if missing?
        # if uri.startswith('sqlite'):
        #     import re
        #     db_file = re.sub("sqlite.*:///", "", uri)
        #     open(db_file, 'a').close()

        try:
            self._db.init_app(app)
        except Exception as e:
            log.critical("Invalid SQLalchemy instance!\n%s" % str(e))

# // TO FIX:
# CHECK IF PASSWORD IS INSIDE THE STRING AND CENSOR IT
        log.debug(
            "App attached to '%s'" % uri)

        # Create database and tables if they don't exist yet
        with app.app_context():
            from rapydo.utils.confs import config

            # TO FIX: this option should go inside the configuration file
            if config.REMOVE_DATA_AT_INIT_TIME:
                log.warning("Removing old data")
                self._db.drop_all()

            log.info("Created database and tables")
            self._db.create_all()

    @classmethod
    def get_instance(cls, models2skip=[], use_models=True):

        if SQLFarm._db is None:

            # Make sure you have models before doing things
            cls.load_models()
            if cls._models_module is None:
                raise AttributeError("Sqlalchemy models unavailable!")

            # We load the instance where the models have been created...
            sql = cls._meta.get_module_from_string(cls._models_module)
            current_instance = sql.db

            # Inject models inside the class
            for name, model in cls._models.items():
                log.verbose("Injecting SQL model '%s'" % name)
                setattr(current_instance, name, model)

            # Save the sqlalchemy reference (to init the app)
            SQLFarm._db = current_instance
            log.debug("SQLAlchemy for Flask initialized")

        return SQLFarm._db
