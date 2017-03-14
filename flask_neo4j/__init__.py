# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

import time
from flask import _app_ctx_stack as stack
# from flask import current_app
from injector import singleton, Module
# from neo4j.v1 import GraphDatabase

####################
# TO FIX: # how to use logs inside this extensions?
# should we make a Flask extension or a Python package out of logging?
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
####################


class Neo4J(object):

    graph_db = None

    def __init__(self, app=None, variables={}, models=[], logger=None):

        import neomodel as neomodel_package
        self.neo = neomodel_package

        self.app = app
        # print("Init service object with Injection", app, self)
        self.variables = variables
        self.log = logger

        if app is not None:
            self.init_app(app)

        if self.log is not None:
            self.log.debug("Vars: %s" % variables)

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
        logger.debug("Connection uri: %s" % self.uri)

        # Try until it's connected
        self.retry()
        logger.info("Connected! %s" % self.neo.db)

        return self.neo.db

    def retry(self, retry_interval=5, max_retries=-1):
        retry_count = 0
        while max_retries != 0 or retry_count < max_retries:
            retry_count += 1
            if retry_count > 1:
                logger.verbose("testing again")
            if self.test_connection():
                break
            else:
                logger.info("Service not available")
                time.sleep(retry_interval)

    def test_connection(self, retry_interval=5, max_retries=0):
        try:
            self.neo.config.DATABASE_URL = self.uri
            self.neo.db.url = self.uri
            self.neo.db.set_connection(self.uri)
            return True
        # except Exception as e:
        except:
            # raise e
            # print("Error", e)
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


class InjectorConfiguration(Module):

    _variables = {}
    _models = {}

    def __init__(self, app):
        self.app = app

    def configure(self, binder):
        neo = Neo4J(self.app, self._variables, self._models)
        # test connection the first time
        neo.connect()
        binder.bind(Neo4J, to=neo, scope=singleton)

    @classmethod
    def set_models(cls, models):
        cls._models = models

    @classmethod
    def set_variables(cls, envvars):
        cls._variables = envvars
