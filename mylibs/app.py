#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App specifications
"""

from .server import microservice, rest_api
from .resources.endpoints import Endpoints
from .config import MyConfigs

from . import get_logger
logger = get_logger(__name__)

######################################################
# From my code: defining automatic Resources
epo = Endpoints(rest_api)
# Verify configuration
resources = MyConfigs().rest()

# Basic configuration (simple): from example class
if len(resources) < 1:
    logger.info("No file configuration found (or no section inside)")
    from mylibs.resources import exampleservices as mymodule
    epo.many_from_module(mymodule)
# Advanced configuration (cleaner): from your module and .ini
else:
    logger.info("Using resources found in configuration")

    for myclass, instance, endpoint, endkey in resources:
        # Load each resource
        epo.create_single(myclass, endpoint, endkey)

####################################
# Take this app from main
microservice.logger.info("*** Our REST API server app is ready ***")
