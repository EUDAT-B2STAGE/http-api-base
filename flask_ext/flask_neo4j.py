# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

import time
from flask import _app_ctx_stack as stack
# from flask import current_app
from flask_ext import get_logger, BaseInjector

log = get_logger(__name__)


class NeoModel(object):

    graph_db = None

    def __init__(self, app=None, variables={}, models=[]):

        import neomodel as neomodel_package
        self.neo = neomodel_package

        self.app = app
        # print("Init service object with Injection", app, self)
        self.variables = variables

        if app is not None:
            self.init_app(app)

        log.very_verbose("Vars: %s" % variables)

    def init_app(self, app):
        # print("\n\n\nflask.ext.Neo4j init_app called\n\n\n")
        app.teardown_appcontext(self.teardown)

    def connect(self):
        # print("variables:", self.variables)

        # Set URI
        self.uri = "bolt://%s:%s@%s:%s" % \
            (
                # User:Password
                'neo4j',
                self.variables.get('password'),
                # Host:Port
                self.variables.get('host'),
                self.variables.get('port'),
            )
        log.debug("Connection uri: %s" % self.uri)

        # Try until it's connected
        self.retry()
        log.info("Connected! %s" % self.neo.db)

        return self.neo.db

    def retry(self, retry_interval=5, max_retries=-1):
        retry_count = 0
        while max_retries != 0 or retry_count < max_retries:
            retry_count += 1
            if retry_count > 1:
                log.verbose("testing again")
            if self.test_connection():
                break
            else:
                log.info("Service not available")
                time.sleep(retry_interval)

    def package_connection(self):
        self.neo.config.DATABASE_URL = self.uri
        self.neo.db.url = self.uri
        self.neo.db.set_connection(self.uri)

    def test_connection(self, retry_interval=5, max_retries=0):
        try:
            self.package_connection()
            return True
        except:
            return False

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'graph_db'):
            # neo does not have an 'open' connection that needs closing
            # ctx.graph_db.close()
            ctx.graph_db = None

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'graph_db'):
                ctx.graph_db = self.connect()
            return ctx.graph_db


class InjectorConfiguration(BaseInjector):

    def configure(self, binder):
        neo = NeoModel(self.app, self._variables, self._models)
        # test connection the first time
        neo.connect()
        binder.bind(NeoModel, to=neo, scope=self.singleton)
