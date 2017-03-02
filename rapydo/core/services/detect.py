# -*- coding: utf-8 -*-

"""
Detect which services are running,
by testing environment variables set by container links

Services:
# graphdb, rethinkdb, elasticsearch, irods and so on
"""

# from __future__ import absolute_import

import os
from rapydo.utils import PRODUCTION
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

#################
services = {}
farm_queue = []

#######################################################
# RELATIONAL DATABASE

SQL_AVAILABLE = False

# Note: with SQL_PROD_AVAILABLE we refer to a real database container
# running and linked (e.g. Mysql or Postgres)
# Not considering sqllite for this variable
SQL_PROD_AVAILABLE = 'SQLDB_NAME' in os.environ and PRODUCTION

if SQL_PROD_AVAILABLE:
    SQL_AVAILABLE = True

if os.environ.get('BACKEND_AUTH_SERVICE', '') == 'relationaldb':
    SQL_AVAILABLE = True
    from rapydo.core.services.sql.alchemy import SQLFarm as service
    # log.debug("Created SQLAlchemy relational DB object")
    farm_queue.append(service)
    # services['sql'] = service

#######################################################
# GRAPH DATABASE
GRAPHDB_AVAILABLE = 'GDB_NAME' in os.environ

if GRAPHDB_AVAILABLE:
    # DO something and inject into 'services'
    from rapydo.core.services.neo4j.graph import GraphFarm as service
    farm_queue.append(service)

#######################################################
# MONGO DB
MONGO_AVAILABLE = 'MONGO_NAME' in os.environ

if MONGO_AVAILABLE:
    # External service if using user/password?
    # TODO: write example into docker-compose production

    # DO something and inject into 'services'
    from rapydo.core.services.mongo.mongodb import MongoFarm as service
    farm_queue.append(service)

#######################################################
# IRODS
IRODS_EXTERNAL = False
IRODS_AVAILABLE = 'RODSERVER_NAME' in os.environ or \
                  'ICAT_1_ENV_IRODS_HOST' in os.environ

if IRODS_AVAILABLE:

    # IRODS 4
    USER_HOME = os.environ['HOME']
    IRODS_HOME = os.path.join(USER_HOME, ".irods")
    if not os.path.exists(IRODS_HOME):
        os.mkdir(IRODS_HOME)
    IRODS_ENV = os.path.join(IRODS_HOME, "irods_environment.json")
    # IRODS_ENV = USER_HOME + "/.irods/.irodsEnv"

    # We may check if iRODS is an external service
    # by verifying if this linked container is provided
    if os.environ.get('RODSERVER_NAME', None) is None:
        IRODS_EXTERNAL = True

    # DO something and inject into 'services'
    from rapydo.core.services.irods.client import IrodsFarm as service
    # services['irods'] = service
    farm_queue.append(service)

#######################################################
# ELASTICSEARCH / OTHERS

ELASTIC_AVAILABLE = 'EL_NAME' in os.environ

if ELASTIC_AVAILABLE:
    from rapydo.core.services.elasticsearch.service import ElasticFarm as service
    farm_queue.append(service)


#######################################################
# REDIS for CELERY TASKS QUEUE

CELERY_AVAILABLE = 'QUEUE_NAME' in os.environ

if CELERY_AVAILABLE:
    from rapydo.core.services.celery.tasks import CeleryFarm as service
    farm_queue.append(service)


#####################################
#####################################

# Create the dictionary of services
for farm in farm_queue:
    service_name = farm.define_service_name()
    log.debug("Adding service '%s' to available array" % service_name)
    services[service_name] = farm
