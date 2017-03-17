# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

from neomodel import db, config
from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class NeoModel(BaseExtension):

    def package_connection(self):

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

        config.DATABASE_URL = self.uri
        db.url = self.uri
        db.set_connection(self.uri)
        return db


class InjectNeo(BaseInjector):

    def configure(self, binder):
        neo = NeoModel(self.app, self._variables, self._models)
        # test connection the first time
        neo.connect()
        binder.bind(NeoModel, to=neo, scope=self.singleton)
