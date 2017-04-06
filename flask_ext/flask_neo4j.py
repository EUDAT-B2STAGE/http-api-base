# -*- coding: utf-8 -*-

""" Neo4j GraphDB flask connector """

import socket
import neo4j
from neomodel import db, config
from flask_ext import BaseInjector, BaseExtension, get_logger
from rapydo.utils.logs import re_obscure_pattern

log = get_logger(__name__)


class NeoModel(BaseExtension):

    def set_connection_exception(self):
        return (
            socket.gaierror,
            neo4j.bolt.connection.ServiceUnavailable
        )

    def custom_connection(self, **kwargs):

        if len(kwargs) > 0:
            print("TODO: use args for connection?", kwargs)

        self.uri = "bolt://%s:%s@%s:%s" % \
            (
                # User:Password
                self.variables.get('user', 'neo4j'),
                self.variables.get('password'),
                # Host:Port
                self.variables.get('host'),
                self.variables.get('port'),
            )
        log.very_verbose("URI IS %s" % re_obscure_pattern(self.uri))

        config.DATABASE_URL = self.uri
        # Ensure all DateTimes are provided with a timezone
        # before being serialised to UTC epoch
        config.FORCE_TIMEZONE = True  # default False
        db.url = self.uri
        db.set_connection(self.uri)
        return db

    def custom_initialization(self, obj=None):
        log.verbose("No initialization for now in neo4j")
        pass


class InjectNeo(BaseInjector):

    def custom_configure(self):
        neo = NeoModel(self.app, self._variables, self._models)
        return NeoModel, neo
