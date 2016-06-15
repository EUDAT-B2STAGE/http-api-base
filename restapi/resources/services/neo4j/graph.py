# -*- coding: utf-8 -*-

""" Graph DB abstraction from neo4j server """

import os
from .... import get_logger
from commons.services import ServiceFarm
from commons.services.uuid import getUUID
from datetime import datetime
import pytz

logger = get_logger(__name__)

###############################
# Verify Graph existence

# Default values, will be overwritten if i find some envs
PROTOCOL = 'http'
HOST = 'agraphdb'
PORT = '7474'
USER = 'neo4j'
PW = USER

try:
    HOST = os.environ['GDB_NAME'].split('/')[2]
    PORT = os.environ['GDB_PORT_7474_TCP_PORT']
    tmp = os.environ['GDB_ENV_NEO4J_AUTH'].split('/')
    USER = tmp[0]
    PW = tmp[1]
except Exception as e:
    logger.critical("Cannot find a Graph database inside the environment\n" +
                    "Please check variable GDB_NAME")
    # raise e
    exit(1)


#######################
# GRAPHDB main object
########################

class MyGraph(object):
    """" A graph db neo4j instance """

    def __init__(self):
        super(MyGraph, self).__init__()
        self.connect()

    def connect(self):
        """ Connection http descriptor """
        try:
            os.environ["NEO4J_REST_URL"] = \
                PROTOCOL + "://" + USER + ":" + PW + "@" + \
                HOST + ":" + PORT + "/db/data"
            logger.debug("Neo4j connection socket is set")
            # print(os.environ["NEO4J_REST_URL"])
        except:
            raise EnvironmentError("Missing URL to connect to graph")
        # Set debug for cypher queries
        os.environ["NEOMODEL_CYPHER_DEBUG"] = "1"

    def cypher(self, query):
        """ Execute normal neo4j queries """
        from neomodel import db
        try:
            results, meta = db.cypher_query(query)
        except Exception as e:
            raise BaseException(
                "Failed to execute Cypher Query: %s\n%s" % (query, str(e)))
            return False
        logger.debug("Graph query. Res: %s\nMeta: %s" % (results, meta))
        return results

    def inject_models(self, models=[]):
        """ Load models mapping Graph entities """

        for model in models:
            # Save attribute inside class with the same name
            logger.debug("Injecting model '%s'" % model.__name__)
            setattr(self, model.__name__, model)

    def createNode(self, model, attributes={}):
        """
            Generic create of a graph node based on the give model
            and applying the given attributes
        """

        node = model()
        node.id = getUUID()
        if hasattr(node, 'created'):
            setattr(node, 'created', datetime.now(pytz.utc))

        if hasattr(node, 'modified'):
            setattr(node, 'modified', datetime.now(pytz.utc))

        for key in attributes:
            setattr(node, key, attributes[key])

        node.save()

        return node





#######################
# Farm to get Graph instances
########################

class GraphFarm(ServiceFarm):

    """ Making some Graphs """

    _graph = None

    def define_service_name(self):
        return 'neo4j'

    def init_connection(self, app):

        # CHECK 1: test the environment
        self._graph = MyGraph()
        logger.debug("Neo4j service seems plugged")

        # CHECK 2: test the models
        # Do not import neomodel before the first check
        # 'cos it will force the system to check for connection
        from neomodel import StructuredNode, StringProperty

        class TestConnection(StructuredNode):
            name = StringProperty(unique_index=True)

        logger.debug("neomodel: checked labeling on active connection")

    def get_instance(self, models2skip=[]):

        if self._graph is None:
            self._graph = MyGraph()
            self.load_models()
            # Remove the ones which developers do not want
            models = set(list(self._models.values())) - set(models2skip)
            self._graph.inject_models(models)
        return self._graph
