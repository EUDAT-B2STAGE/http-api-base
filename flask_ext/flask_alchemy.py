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

    def package_connection(self):

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

            with self.app.app_context():
                self.mydb.create_all()

        return self.mydb


class SqlInjector(BaseInjector):

    def custom_configure(self):
        sql = SqlAlchemy(self.app, self._variables, self._models)
        # test connection the first time
        sql.connect()

        # ########################
        # from sqlalchemy import create_engine  # , MetaData
        # from sqlalchemy.orm import scoped_session, sessionmaker

        # engine = create_engine('sqlite:////tmp/testdb', convert_unicode=True)
        # # metadata = MetaData()
        # db_session = scoped_session(
        #     sessionmaker(autocommit=False, autoflush=False, bind=engine))
        # print("db", db_session)

        return SqlAlchemy, sql
