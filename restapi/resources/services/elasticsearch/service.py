# -*- coding: utf-8 -*-

"""
Quick search text (mostly for web UI).
Enter ElasticSearch!
"""

# from __future__ import absolute_import
import os

from collections import OrderedDict
from commons.logs import get_logger
from commons.services import ServiceFarm, ServiceObject
# from commons.services.uuid import getUUID
from commons.services.uuid import getUUIDfromString
# from datetime import datetime
# import pytz

HOST = os.environ['EL_NAME'].split('/').pop()
PORT = os.environ['EL_PORT'].split(':').pop()

ES_SERVICE = {"hosts": [{'host': HOST, 'port': PORT}], 'timeout': 5}

logger = get_logger(__name__)


#######################
# ElasticSearch main object
########################
class BeElastic(ServiceObject):

    def __init__(self):

        # super(BeElastic, self).__init__()
        from elasticsearch_dsl.connections import connections
        self._connection = connections.create_connection(**ES_SERVICE)

    def get_or_create(self, DocumentClass, args={}):
        """
        Inspired by `neomodel` function get_or_create
        I want to send args which will create the document inside the index
        only if the data is not there yet.

        To make sure we do we use the update with an ID manually generated.
        If we create the same string with same args,
        the hash will be our unique ID.

        The solution is to build
        an OrderedDict from the original args dictionary,
        which converted to string will always be the same with same parameters.
        """

        if len(args) < 1:
            raise AttributeError("Cannot create id from no arguments")

        # Since the ID with same parameters is the same
        # the document will be created only with non existing data
        ordered_args = OrderedDict(sorted(args.items()))
        id = getUUIDfromString(str(ordered_args))

        # If you want to check existence
        obj = DocumentClass.get(id=id, ignore=404)
        # print("Check", id, check)
        if obj is None:
            logger.debug("Creating a new document '%s'" % id)

            # Put the id in place
            args['meta'] = {'id': id}
            # print("ARGS", args)
            obj = DocumentClass(**args)
            # obj.update()
            obj.save()

        return obj


#######################
# Farm to get Elastic instances
########################
class ElasticFarm(ServiceFarm):

    _instance = None

    @staticmethod
    def define_service_name():
        return 'elasticsearch'

    def init_connection(self, app):

        name = self.define_service_name()

        # Elasticsearch logger to be silenced
        # in checking the existing connection
        import logging
        loggerES = logging.getLogger('elasticsearch')
        loggerES.setLevel(logging.CRITICAL)
        loggerUrlib = logging.getLogger('urllib3')
        loggerUrlib.setLevel(logging.CRITICAL)

        # CHECK 1: verify the library

        # self._instance = BeElastic()
        # logger.debug("Plugging '%s' service" % name)
        self.get_instance()

        self._instance._connection.ping()
        logger.debug("'%s' service seems plugged" % name)

        # # CHECK 2: test the models
        # from elasticsearch_dsl import DocType, String

        # class TestConnection(DocType):
        #     empty = String()

        #     class Meta:
        #         index = 'justatest'

        # self.init_models({'test': TestConnection})

        # del self._instance
        # self._instance._connection.close()

    @staticmethod
    def init_models(models):
        """
        Init a model and create the index if not existing
        """
        from elasticsearch_dsl import Index
        for _, model_obj in models.items():

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

    @classmethod
    def get_instance(cls, models2skip=[], use_models=True):

        if ElasticFarm._instance is None:

            # Connect
            ElasticFarm._instance = BeElastic()

            # Use DSL models
            if use_models:
                cls.init_models(cls.load_models())

                # Remove the ones which developers do not want
                models = set(list(cls._models.values())) - set(models2skip)
                ElasticFarm._instance.inject_models(models)

        return ElasticFarm._instance
