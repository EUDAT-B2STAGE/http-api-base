# -*- coding: utf-8 -*-

""" Graph DB abstraction from neo4j server """

import os
from commons.meta import Meta
from .... import get_logger
from commons.databases import DBinstance

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

    def load_models(self, models=[]):
        """ Load models mapping Graph entities """

        for model in models:
            # Save attribute inside class with the same name
            logger.debug("Loading model '%s'" % model.__name__)
            setattr(self, model.__name__, model)

    def other(self):
        return self


#######################
# Farm to get Graph instances
########################

class GraphFarm(DBinstance):

    """ Making some Graphs """

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

    def get_instance(self,
       pymodule_with_models='.resources.services.neo4j.models',
       models2skip=[]):

        # Relative import: Add the name of the package as prefix
        module = __package__.split('.')[0] + pymodule_with_models
        self._graph = MyGraph()
        meta = Meta()

# // TO FIX:
# load only models once into static class, please!

        models_found = \
            meta.get_new_classes_from_module(
                meta.get_module_from_string(module))
        models = set(list(models_found.values())) - set(models2skip)
        self._graph.load_models(models)
        return self._graph
