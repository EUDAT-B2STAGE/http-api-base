# -*- coding: utf-8 -*-

""" Alchemy extension wrapper
for the existing Flask-SQLalchemy

NOTE: Flask Sqlalchemy needs to have models defined on existing instance;
for this reason we create the sql instance where models are defined.

For future lazy alchemy: http://flask.pocoo.org/snippets/22/
"""

import sqlalchemy
from rapydo.utils.meta import Meta
from rapydo.confs import BACKEND_PACKAGE, CUSTOM_PACKAGE
from flask_ext import BaseInjector, BaseExtension, get_logger
from rapydo.utils.logs import re_obscure_pattern

log = get_logger(__name__)


class SqlAlchemy(BaseExtension):

    def set_connection_exception(self):
        return (sqlalchemy.exc.OperationalError, )

    def custom_connection(self, **kwargs):

        if len(kwargs) > 0:
            print("TODO: use args for connection?", kwargs)

        uri = 'postgresql://%s:%s@%s:%s/%s' % (
            self.variables.get('user'),
            self.variables.get('password'),
            self.variables.get('host'),
            self.variables.get('port'),
            self.variables.get('db')
        )

        log.very_verbose("URI IS %s" % re_obscure_pattern(uri))

        # TODO: in case we need different connection binds
        # (multiple connections with sql) then:
        # SQLALCHEMY_BINDS = {
        #     'users':        'mysqldb://localhost/users',
        #     'appmeta':      'sqlite:////path/to/appmeta.db'
        # }

        self.app.config['SQLALCHEMY_POOL_TIMEOUT'] = 3
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = uri

        obj_name = 'db'
        m = Meta()
        # search the original sqlalchemy object into models
        db = m.obj_from_models(obj_name, self.name, CUSTOM_PACKAGE)
        if db is None:
            log.warning("No sqlalchemy db imported in custom package")
            db = m.obj_from_models(obj_name, self.name, BACKEND_PACKAGE)
        if db is None:
            log.critical_exit(
                "Could not get %s within %s models" % (obj_name, self.name))

        return db

    def custom_init(self, db=None):

        # # TO FIX: this option would go inside the configuration file?
        # if config.REMOVE_DATA_AT_INIT_TIME:
        # if self.variables('remove_data_at_init_time'):
        #     log.warning("Removing old data")
        #     self._db.drop_all()

        # recover instance with the parent method
        if db is None:
            db = super().custom_init()

        # do init_app on the original flask sqlalchemy extension
        db.init_app(self.app)

        # careful on what you do with app context on sqlalchemy
        with self.app.app_context():

            # check connection
            from sqlalchemy import text
            sql = text('SELECT 1')
            db.engine.execute(sql)

            # all is fine: now create table if they don't exist
            db.create_all()

        return db


class SqlInjector(BaseInjector):
    pass
