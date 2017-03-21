# -*- coding: utf-8 -*-

""" Alchemy extension wrapper
for the existing Flask-SQLalchemy

NOTE: Flask Sqlalchemy needs to have models defined on existing instance;
for this reason we create the sql instance where models are defined.

For future lazy alchemy: http://flask.pocoo.org/snippets/22/
"""

from rapydo.utils.meta import Meta
from rapydo.confs import BACKEND_PACKAGE, CUSTOM_PACKAGE
from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class SqlAlchemy(BaseExtension):

    def custom_connection(self):

        uri = 'postgresql://%s:%s@%s:%s/%s' % (
            self.variables.get('user'),
            self.variables.get('password'),
            self.variables.get('host'),
            self.variables.get('port'),
            self.variables.get('db')
        )
        # TO FIX: remove password from uri when printing
        log.verbose("URI IS %s" % uri)

        # TODO: in case we need different connection binds
        # SQLALCHEMY_BINDS = {
        #     'users':        'mysqldb://localhost/users',
        #     'appmeta':      'sqlite:////path/to/appmeta.db'
        # }

        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = uri

        # Avoid ever creating a second connection
        # due to the already existing flask-SQLalchemy original extension
        if not hasattr(self, 'mydb'):
            obj_name = 'db'
            m = Meta()
            # search the original sqlalchemy object into models
            tmp = m.obj_from_models(obj_name, self.name, CUSTOM_PACKAGE)
            if tmp is None:
                log.warning("No sqlalchemy db imported in custom package")
                tmp = m.obj_from_models(obj_name, self.name, BACKEND_PACKAGE)
                if tmp is None:
                    log.error("Could not get %s within %s models" %
                              (obj_name, self.name))
                    exit(1)
            self.mydb = tmp

            # do init_app on the extension
            self.mydb.init_app(self.app)

        return self.mydb

    def custom_initialization(self):
        obj = self.get_object()

        # # TO FIX: this option should go inside the configuration file
        # if config.REMOVE_DATA_AT_INIT_TIME:
        # if self.variables('remove_data_at_init_time'):
        #     log.warning("Removing old data")
        #     self._db.drop_all()

        obj.create_all()


class SqlInjector(BaseInjector):

    def custom_configure(self):
        sql = SqlAlchemy(self.app, self._variables, self._models)
        return SqlAlchemy, sql
