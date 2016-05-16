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


#######################################################
# GRAPH DATABASE
GRAPHDB_AVAILABLE = 'GDB_NAME' in os.environ

#######################################################
# RETHINKDB
RDB_AVAILABLE = False
MODELS = []

if 'RDB_NAME' in os.environ:
    from .resources.services.rethink import load_models, wait_for_connection
    # Look for models
    MODELS = load_models()
    if len(MODELS) > 0:
        RDB_AVAILABLE = True
        wait_for_connection()
        logger.info("Found RethinkDB container")
