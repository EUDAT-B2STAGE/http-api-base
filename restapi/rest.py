# -*- coding: utf-8 -*-

"""
App specifications
"""

from __future__ import absolute_import

from flask_restful import Api as RestFulApi
from .resources.farm import EndpointsFarmer

from commons.globals import mem
from commons.logs import get_logger

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

        ##################################
        # What we are skipping

        # from functools import wraps
        # from werkzeug.wrappers import Response as ResponseBase
        # from flask_restful.utils import unpack

        # @wraps(resource)
        # def wrapper(*args, **kwargs):

        #     print("REST IN")
        #     resp = resource(*args, **kwargs)
        #     print("REST OUT")

        #     from .response import ResponseElements
        #     if isinstance(resp, ResponseElements):
        #         return resp

        #     # There may be a better way to test
        #     if isinstance(resp, ResponseBase):
        #         return resp
        #     data, code, headers = unpack(resp)
        #     return self.make_response(data, code, headers=headers)
        # return wrapper
        ##################################

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

        # # DEPRECATED
        # from .resources import exampleservices as mymodule
        # epo.many_from_module(mymodule)
        # log.debug("Loaded example class instead")

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
        log.info("Found one or more schema to expose")
        # log.pp(se)
        epo.add(se)

    ####################################
    # The end
    return epo
