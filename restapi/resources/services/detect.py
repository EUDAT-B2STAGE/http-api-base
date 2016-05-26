# -*- coding: utf-8 -*-

"""
Detect which services are running,
by testing environment variables set by container links

Services:
# graphdb, rethinkdb, elasticsearch, irods and so on
"""

from __future__ import absolute_import
import os

from ... import get_logger
logger = get_logger(__name__)

#################
services = {}

#######################################################
# RELATIONAL DATABASE
### Detect SQL database?
### like sqllite, postgres, mysql

# DO something and inject into 'services'

#######################################################
# GRAPH DATABASE
GRAPHDB_AVAILABLE = 'GDB_NAME' in os.environ

if GRAPHDB_AVAILABLE:
    # DO something and inject into 'services'
    from .neo4j.graph import GraphFarm as service
    services['neo4j'] = service

#######################################################
# IRODS

#??

#######################################################
# ELASTICSEARCH

#??

# #######################################################
# # RETHINKDB
# RDB_AVAILABLE = False
# MODELS = []

# if 'RDB_NAME' in os.environ:
#     from .resources.services.rethink import load_models, wait_for_connection
#     # Look for models
#     MODELS = load_models()
#     if len(MODELS) > 0:
#         RDB_AVAILABLE = True
#         wait_for_connection()
#         logger.info("Found RethinkDB container")
