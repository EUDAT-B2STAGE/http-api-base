# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

from flask import Flask
from flask import _app_ctx_stack as stack
# from flask import current_app
from neo4j.v1 import GraphDatabase


class Neo4J(object):

    def __init__(self, app=None, variables={}, logger=None):
        self.app = app
        self.variables = variables
        self.log = logger
        if app is not None:
            self.init_app(app)
        if self.log is not None:
            self.log.debug("Vars: %s" % variables)

    def init_app(self, app):
        print("flask.ext.Neo4j init_app called")
        # TODO: set any default to flask config?
        # print("TEST VARIABLES", self.variables)
        # app.config.setdefault('GRAPH_DATABASE', ':memory:')
        app.teardown_appcontext(self.teardown)

    def connect(self):
        # print("TEST VARIABLES", self.variables)
        import os
        driver = GraphDatabase.driver(
            "bolt://%s:%s" % (
                os.environ.get("GRAPHDB_HOST"),
                os.environ.get("GRAPHDB_PORT"),
                # self.variables.get('host'),
                # self.variables.get('port'),
            ),
            auth=(
                'neo4j',
                os.environ.get("GRAPHDB_PASSWORD")
                # self.variables.get('password')
            ),
        )
        print("Connected", driver)
        return driver

        # # TODO: inject configuration from env var to flask.config
        # # return sqlite3.connect(current_app.config['SQLITE3_DATABASE'])
        # import os
        # from neomodel import config
        # # Ensure all DateTimes are provided with a timezone
        # # before being serialised to UTC epoch
        # config.FORCE_TIMEZONE = True  # default False
        # config.DATABASE_URL = "bolt://%s:%s@%s" % \
        #     (
        #         'neo4js',
        #         os.environ.get('GRAPHDB_PASSWORD'),
        #         os.environ.get('GRAPHDB_HOST'),
        #     )
        # # from neomodel import db
        # # db.set_connection('bolt://neo4j:neo4j@localhost:7687')
        # return None

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'graphdb'):
            # neo does not have an 'open' connection that needs closing
            # ctx.graphdb.close()
            ctx.graph_db = None

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'graphdb'):
                ctx.graphdb = self.connect()
            return ctx.graphdb
