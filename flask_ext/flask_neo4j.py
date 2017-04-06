# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

from neomodel import db, config
from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class NeoModel(BaseExtension):

    def custom_connection(self):

        self.uri = "bolt://%s:%s@%s:%s" % \
            (
                # User:Password
                self.variables.get('user', 'neo4j'),
                self.variables.get('password'),
                # Host:Port
                self.variables.get('host'),
                self.variables.get('port'),
            )
        log.debug("Connection uri: %s" % self.uri)

        config.DATABASE_URL = self.uri
        # Ensure all DateTimes are provided with a timezone
        # before being serialised to UTC epoch
        config.FORCE_TIMEZONE = True  # default False
        db.url = self.uri
        db.set_connection(self.uri)
        return db

    def custom_initialization(self):
        pass


class InjectNeo(BaseInjector):

    def custom_configure(self):
        neo = NeoModel(self.app, self._variables, self._models)
        return NeoModel, neo
