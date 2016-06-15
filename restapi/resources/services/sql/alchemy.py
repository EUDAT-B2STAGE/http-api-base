# -*- coding: utf-8 -*-

"""
SQL Alchemy:
sqllite, MySQL or Postgres
"""

# from __future__ import absolute_import
from commons.services import ServiceFarm
from commons.logs import get_logger

logger = get_logger(__name__)


class SQLFarm(ServiceFarm):
    """

    Creating the farm for SQLalchemy as an API service.

    NOTE: Flask Sqlalchemy needs to have models defined on existing instance;
    for this reason we create the sql instance where models are defined.
    """

    _db = None

    def define_service_name(self):
        return 'sql'

    def init_connection(self, app):
        self.get_instance()
        try:
            self._db.init_app(app)
        except Exception as e:
            logger.critical("Invalid SQLalchemy instance!\n%s" % str(e))
# // TO FIX:
# CHECK IF PASSWORD IS INSIDE THE STRING AND CENSOR IT
        logger.debug(
            "App attached to '%s'" % app.config.get('SQLALCHEMY_DATABASE_URI'))
        # Create database and tables if they don't exist yet
        with app.app_context():
            self._db.create_all()

    def get_instance(self):

        if self._db is None:

            # Make sure you have models before doing things
            self.load_models()
            if self._models_module is None:
                raise AttributeError("Sqlalchemy models unavailable!")

            # We load the instance where the models have been created...
            sql = self._meta.get_module_from_string(self._models_module)
            current_instance = sql.db

            # Inject models inside the class
            for name, model in self._models.items():
                logger.debug("Injecting SQL model '%s'" % name)
                setattr(current_instance, name, model)

            # Save the sqlalchemy reference (to init the app)
            self._db = current_instance
            logger.debug("SQLAlchemy for Flask initialized")

        return self._db
