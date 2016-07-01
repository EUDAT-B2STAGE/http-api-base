# -*- coding: utf-8 -*-

"""
Quick search text (mostly for web UI).
Enter ElasticSearch!
"""

# from __future__ import absolute_import
from commons.logs import get_logger
from elasticsearch import Elasticsearch
from commons.services import ServiceFarm
# from commons.services.uuid import getUUID
# from datetime import datetime
# import pytz

ES_SERVER = 'el'
ES_SERVICE = {"host": ES_SERVER, "port": 9200}

logger = get_logger(__name__)


#######################
# ElasticSearch main object
########################
class BeElastic(object):

    def __init__(self):
        super(BeElastic, self).__init__()
        self._connection = Elasticsearch(**ES_SERVICE)
        logger.debug("Connected")

    def index_up(self, index_name):

        # Create if not exist
        if not self._connection.indices.exists(index=index_name):
            self._connection.indices.create(index=index_name, body={})


#######################
# Farm to get Elastic instances
########################
class ElasticFarm(ServiceFarm):

    _link = None

    @staticmethod
    def define_service_name():
        return 'elasticsearch'

    def init_connection(self, app):
        return self.get_instance()

    def get_instance(self, models2skip=[], use_models=True):
        if self._link is None:
            self._link = BeElastic()
            logger.debug("ElasticSearch service seems plugged")

        return self._link
