# -*- coding: utf-8 -*-

"""
Quick search text (mostly for web UI).
Enter ElasticSearch!

Note: to delete all data with ipython from the server:
```
es = Elasticsearch(host='el')
for index in es.indices.get_aliases().keys():
    es.indices.delete(index)
```
"""

# from __future__ import absolute_import
import os
import logging
# import pytz

from collections import OrderedDict
from commons.logs import get_logger
from commons.services import ServiceFarm, ServiceObject
# from commons.services.uuid import getUUID
from commons.services.uuid import getUUIDfromString
# from datetime import datetime
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import Index

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
        self._connection = connections.create_connection(**ES_SERVICE)

    @staticmethod
    def dict2ordered_string(mydict):

        if mydict is None or not isinstance(mydict, dict) or len(mydict) < 1:
            return ""

        return str(OrderedDict(sorted(mydict.items())))

    def get_or_create(self, DocumentClass, args={}, forced_id=None):
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

        id = None
        if forced_id is None:
            # Since the ID with same parameters is the same
            # the document will be created only with non existing data
            id = getUUIDfromString(self.dict2ordered_string(args))
        else:
            id = forced_id

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

    def get_or_create_suggestion(self, DocumentClass, text,
                                 attribute='suggestme', output=None,
                                 weight=1, payload=None):

        input = [text]
        text_lower = text.lower()
        if text != text_lower:
            input.append(text_lower)

        if output is None:
            output = text

        suggestion = {
            "input": input,
            "output": output,
            "payload": payload,
        }

        if weight > 1:
            suggestion["weight"] = weight

        # force the new id with the subnested dictionary
        id = getUUIDfromString(self.dict2ordered_string(suggestion))

        return self.get_or_create(
            DocumentClass, {attribute: suggestion}, forced_id=id)

    def clean_all(self):
        logger.warning("Removing all data")
        for index in self._connection.indices.get_aliases().keys():
            self._connection.indices.delete(index)

    def search_suggestion(self, DocumentClass, keyword,
                          manipulate_output=None, attribute='suggestme'):
        """
        A search for a suggestion field
        """

        output = []
        suggest = None
        try:
            suggest = DocumentClass.search() \
                .suggest('data', keyword, completion={'field': attribute}) \
                .execute_suggest()

        except Exception as e:
            logger.warning("Suggestion error:\n%s" % e)
            return self.force_response(errors={'suggest': 'internal error'})
        # finally:
        #     if suggest is None or 'data' not in suggest:
        #         return output

        # IF using execute_suggest...
        # print(suggest.data)
        for results in suggest.data:
            for result in results.options:
                if manipulate_output is not None:
                    result = manipulate_output(result)
                output.append(result)

        return output


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
        for _, model_obj in models.items():

# // TO BE FIXED
# waiting for https://github.com/elastic/elasticsearch-dsl-py/pull/272
            i = Index(model_obj._doc_type.index)
            if i.exists():
                i.close()
            model_obj.init()
            i.open()
            # print("Es index",
            #       model_obj._doc_type.name, model_obj._doc_type.index)
            # # model_obj._doc_type.refresh()

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
