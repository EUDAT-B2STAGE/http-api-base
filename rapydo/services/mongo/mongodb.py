# -*- coding: utf-8 -*-

""" MongoDB abstraction for core http api driver connector """

# from __future__ import absolute_import

import os

# from pymongo import MongoClient
from pymodm import connect
# from pymongo.write_concern import WriteConcern
from pymodm import MongoModel, fields

# try:
#     # Python 3.x
#     from urllib.parse import quote_plus
# except ImportError:
#     # Python 2.x
#     from urllib import quote_plus

from rapydo.services import ServiceFarm, ServiceObject
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

# uri = "mongodb://%s:%s@%s" % (
#     quote_plus(user), quote_plus(password), host)
# client = MongoClient(uri)

# Default values, will be overwritten if i find some envs
PROTOCOL = 'mongodb'
HOST = 'ourmongodbinstance'
PORT = 27017
# USER = 'neo4j'
# PW = USER

try:
    HOST = os.environ['MONGO_NAME'].split('/').pop()
    PORT = os.environ['MONGO_PORT'].split(':').pop()
    # USER, PW = os.environ['GDB_ENV_NEO4J_AUTH'].split('/')
except Exception as e:
    log.critical("Cannot find a MongoDB database inside the environment\n" +
                 "Please check variable MONGO_NAME")
    # raise e
    exit(1)


#######################
# MongoDB main object
########################

class MyMongoDb(ServiceObject):
    """" A graph db neo4j instance """

    DEFAULTDB = 'test'

    def __init__(self, db=None):
        super(MyMongoDb, self).__init__()
        self.connect(db=db)

    def connect(self, db=None):

        if db is None:
            db = self.DEFAULTDB

        uri = "mongodb://%s:%s/%s" % (HOST, PORT, db)
        if db == self.DEFAULTDB:
            connect(uri)
        else:
            log.debug("Connected to db %s" % db)
            connect(uri, alias=db)


#######################
# Farm to get instances
########################

class MongoFarm(ServiceFarm):

    """ Making some Mongos """

    _mongo = None

    @staticmethod
    def define_service_name():
        return 'mongo'

    def init_connection(self, app):

        ################################
        # CHECK 1: test the environment
        from pymongo import MongoClient
        # TO FIX: pymongo timeout?
        client = MongoClient(
            host=HOST, port=27017, connect=True, connectTimeoutMS=1000)
        db = client.test_database
        # Avoid timeout to check connection the first time
        # http://api.mongodb.com/python/current/
        #   faq.html#how-do-i-change-the-timeout-value-for-cursors
        list(db.posts.find(no_cursor_timeout=True))
        # db.posts.insert_one({'prova': 'test'}).inserted_id
        client.close()

        ################################
        # CHECK 2: test the models on db 'test'
        self._mongo = MyMongoDb()
        log.verbose("A mongo service could be plugged")

        class JustATest(MongoModel):
            onlyfield = fields.CharField()

        try:
            for test in JustATest.objects.all():
                pass
        except Exception:
            raise EnvironmentError("Failed to test mongo connection")

        log.debug("pymongo+pyodm: checked active connection")
        del self._mongo

    @classmethod
    def get_instance(cls, models2skip=[], use_models=True, dbname=None):

        if MongoFarm._mongo is None:
            MongoFarm._mongo = MyMongoDb(db=dbname)
            if use_models:
                cls.load_models()
                # Remove the ones which developers do not want
                models = set(list(cls._models.values())) - set(models2skip)
                MongoFarm._mongo.inject_models(models)

        return MongoFarm._mongo
