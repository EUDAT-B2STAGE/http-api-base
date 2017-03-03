# -*- coding: utf-8 -*-

"""
App specifications
"""

from flask_restful import Api as RestFulApi
from rapydo.farm import EndpointsFarmer

from rapydo.utils.globals import mem
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


# Hack the original class to remove the response making...
class Api(RestFulApi):

    def output(self, resource):
        """
        The original method here was trying to intercept the Response before
        Flask could build it, by writing a decorator on the resource and force
        'make_response' on unpacked elements.

        This ruins our plan of creating our standard response,
        so I am overriding it to JUST TO AVOID THE DECORATOR
        """

        return resource


####################################
# REST to be activated inside the app factory
log.debug(
    "Create endpoints w/ [%s, %s]" % (Api, EndpointsFarmer))


def create_endpoints(epo, security=False, debug=False):
    """
    A single method to add all endpoints
    """

    # ####################################
    # Use configuration built with swagger
    resources = mem.customizer._endpoints

    ####################################
    # Basic configuration (simple): from example class
    if len(resources) < 1:
        log.warning("No custom endpoints found!")

        raise AttributeError("Follow the docs and define your endpoints")

    log.debug("Using resources defined within swagger")

    for resource in resources:

        if not security:
            # TODO: CHECK can we allow a server startup with no security?
            raise NotImplementedError("No way to remove security with swagger")

        # TODO: CHECK is there any way to remove farm.py ?
        epo.add(resource)

    # Enable all schema endpoints to be mapped with this extra step
    se = mem.customizer._schema_endpoint
    if len(se.uris) > 0:
        log.debug("Found one or more schema to expose")
        epo.add(se)

    ####################################
    # The end
    return epo
