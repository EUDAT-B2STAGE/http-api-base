# -*- coding: utf-8 -*-

"""
Quick search text (mostly for web UI).
Enter ElasticSearch!
"""

# from __future__ import absolute_import
from commons.logs import get_logger
from commons.services import ServiceFarm, ServiceObject
# from commons.services.uuid import getUUID
# from datetime import datetime
# import pytz

ES_SERVER = 'el'
ES_SERVICE = {"host": ES_SERVER, "port": 9200}

logger = get_logger(__name__)


#######################
# ElasticSearch main object
########################
class BeElastic(ServiceObject):

    def __init__(self):

        # super(BeElastic, self).__init__()

        ## Original
        # from elasticsearch import Elasticsearch
        # self._connection = Elasticsearch(**ES_SERVICE)

        ## New feature (ORM like)
        from elasticsearch_dsl.connections import connections
        self._connection = connections.create_connection(**ES_SERVICE)
        # from elasticsearch_dsl import Search
        # s = Search()
        # response = s.execute()
        # print("TEST", response)

        logger.debug("Connected")

## The index is already created if not existing by the model .init() function

    # def index_up(self, index_name=None):

    #     # if index_name is None:
    #     #     index_name = self._index

    #     raise NotImplementedError("To be modified for DSL library")

    #     ## Original
    #     # Create if not exist
    #     if not self._connection.indices.exists(index=index_name):
    #         self._connection.indices.create(index=index_name, body={})

    #     ## New feature (ORM like)
    #     # TO DO


#######################
# Farm to get Elastic instances
########################
class ElasticFarm(ServiceFarm):

    _instance = None

    @staticmethod
    def define_service_name():
        return 'elasticsearch'

    def init_connection(self, app):
        return self.get_instance()

    def get_instance(self, models2skip=[], use_models=True):
        if self._instance is None:

            # Connect
            self._instance = BeElastic()
            logger.debug("ElasticSearch service seems plugged")

            # Use DSL models
            if use_models:
                self.load_models()
                # Remove the ones which developers do not want
                models = set(list(self._models.values())) - set(models2skip)
                self._instance.inject_models(models)

                from elasticsearch_dsl import Index
                for _, model_obj in self.load_models().items():

# // TO BE FIXED
# waiting for https://github.com/elastic/elasticsearch-dsl-py/pull/272
                    i = Index(model_obj._doc_type.index)
                    if i.exists():
                        i.close()
                    model_obj.init()
                    i.open()
                    print("Es index",
                          model_obj._doc_type.name, model_obj._doc_type.index)
                    # model_obj._doc_type.refresh()

        return self._instance
