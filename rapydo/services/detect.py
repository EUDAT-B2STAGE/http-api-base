# -*- coding: utf-8 -*-

"""
Detect which services are running,
by testing environment variables set by container links
"""

import os
from rapydo.utils.meta import Meta
from rapydo.confs import BACKEND_PACKAGE
from rapydo.utils.formats.yaml import load_yaml_file
from rapydo.utils.logs import get_logger

log = get_logger(__name__)
services = {}


"""
# Refactor "detection"
due to compose v2/v3 not providing anymore env vars
from linked containers

--

- read from host variables
    - set variables in .env (for now)
        - note: .env may not work in swarm deploy mode
    - read from configuration and set them with do.py (in the future)
- variables are needed to ENABLE a service
    - services/dbs should have standard names
    - variables also set if a service is external

"""

CORE_CONFIG_PATH = os.path.join(BACKEND_PACKAGE, 'confs')
services_configuration = load_yaml_file('services', path=CORE_CONFIG_PATH)
# log.pp(services_configuration)

auth_service = os.environ.get('AUTH_SERVICE')
if auth_service is None:
    raise ValueError("You MUST specify a service for authentication")
else:
    log.verbose("Authe service '%s'" % auth_service)

meta = Meta()

for service in services_configuration:

    name = service.get('name')
    prefix = service.get('prefix') + '_'
    log.very_verbose("Service: %s" % name)
    # log.pp(service)

    # Is this service enabled?
    enable_var = prefix.upper() + 'ENABLE'

    if os.environ.get(enable_var, False):
        log.info("Service *%s* requested for enabling" % name)

        # Is this service external?
        external_var = prefix.upper() + 'EXTERNAL'
        if os.environ.get(external_var) is None:
            os.environ[external_var] = "False"

        ###################
        # Read variables
        variables = {}
        for var, value in os.environ.items():
            if var == enable_var:
                continue
            var = var.lower()
            if var.startswith(prefix):
                key = var[len(prefix):]
                variables[key] = value

        ###################
        # Load module and get class and configuration
        module = meta.get_module_from_string(
            'flask_ext.' + service.get('extension'))
        print("TEST MODULE", module)
        Class = getattr(module, service.get('class'))
        Configurator = getattr(module, service.get('injector'))
        Configurator.set_variables(variables)

        # base_models_module = "rapydo.models.SOME"
        # custom_models_module = "eudat.models.SOME"
        # Configurator.set_models(base_models_module, custom_models_module)

        # ###################
        # # # MOVE THIS INTO FARM
        # # # Is this service optional?
        # # variables.get('optional', False)
        # # print(variables)

        # Save into mem
        services[name] = Configurator

    else:
        log.very_verbose("Skipping service %s" % name)

        # ###################
        # print("\n\nEXIT DEBUG")
        # exit(1)

# log.pp(mem)
# exit(1)
#
# #######################################################
# farm_queue = []

# #######################################################
# # RELATIONAL DATABASE

# SQL_AVAILABLE = False

# # Note: with SQL_PROD_AVAILABLE we refer to a real database container
# # running and linked (e.g. Mysql or Postgres)
# # Not considering sqllite for this variable
# SQL_PROD_AVAILABLE = 'SQLDB_NAME' in os.environ and PRODUCTION

# if SQL_PROD_AVAILABLE:
#     SQL_AVAILABLE = True

# if os.environ.get('BACKEND_AUTH_SERVICE', '') == 'relationaldb':
#     SQL_AVAILABLE = True
#     from rapydo.services.sql.alchemy import SQLFarm as service
#     # log.debug("Created SQLAlchemy relational DB object")
#     farm_queue.append(service)
#     # services['sql'] = service

# #######################################################
# # GRAPH DATABASE
# GRAPHDB_AVAILABLE = 'GDB_NAME' in os.environ

# if GRAPHDB_AVAILABLE:
#     # DO something and inject into 'services'
#     from rapydo.services.neo4j.graph import GraphFarm as service
#     farm_queue.append(service)

# #######################################################
# # MONGO DB
# MONGO_AVAILABLE = 'MONGO_NAME' in os.environ

# if MONGO_AVAILABLE:
#     # External service if using user/password?
#     # TODO: write example into docker-compose production

#     # DO something and inject into 'services'
#     from rapydo.services.mongo.mongodb import MongoFarm as service
#     farm_queue.append(service)

# #######################################################
# # IRODS
# IRODS_EXTERNAL = False
# IRODS_AVAILABLE = 'RODSERVER_NAME' in os.environ or \
#                   'ICAT_1_ENV_IRODS_HOST' in os.environ

# if IRODS_AVAILABLE:

#     # IRODS 4
#     USER_HOME = os.environ['HOME']
#     IRODS_HOME = os.path.join(USER_HOME, ".irods")
#     if not os.path.exists(IRODS_HOME):
#         os.mkdir(IRODS_HOME)
#     IRODS_ENV = os.path.join(IRODS_HOME, "irods_environment.json")
#     # IRODS_ENV = USER_HOME + "/.irods/.irodsEnv"

#     # We may check if iRODS is an external service
#     # by verifying if this linked container is provided
#     if os.environ.get('RODSERVER_NAME', None) is None:
#         IRODS_EXTERNAL = True

#     # DO something and inject into 'services'
#     from rapydo.services.irods.client import IrodsFarm as service
#     # services['irods'] = service
#     farm_queue.append(service)

# #######################################################
# # ELASTICSEARCH / OTHERS

# ELASTIC_AVAILABLE = 'EL_NAME' in os.environ

# if ELASTIC_AVAILABLE:
#     from rapydo.services.elasticsearch.service import ElasticFarm as service
#     farm_queue.append(service)


# #######################################################
# # REDIS for CELERY TASKS QUEUE

# CELERY_AVAILABLE = 'QUEUE_NAME' in os.environ

# if CELERY_AVAILABLE:
#     from rapydo.services.celery.tasks import CeleryFarm as service
#     farm_queue.append(service)


# #####################################
# #####################################

# # Create the dictionary of services
# for farm in farm_queue:
#     service_name = farm.define_service_name()
#     log.debug("Adding service '%s' to available array" % service_name)
#     services[service_name] = farm

# print("SERVICES", services)
# exit(1)
