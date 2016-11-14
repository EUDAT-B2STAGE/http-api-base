# -*- coding: utf-8 -*-

"""
App specifications
"""

from __future__ import division
from . import myself, lic
from commons.logs import get_logger
from flask_restful import Api as RestFulApi
from .resources.farm import EndpointsFarmer
from .config import MyConfigs

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


# Hack the original class to remove the response making...
class Api(RestFulApi):

    def output(self, resource):
        """
        The original method here was trying to intercept the Response before
        Flask could build it, by writing a decorator on the resource and force
        'make_response' on unpacked elements.

        This ruins our plan of creating our standard response,
        so I am overriding it to just avoid the decorator
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
logger.debug(
    "Restful classes to create endpoints: [%s, %s]" % (Api, EndpointsFarmer))


def create_endpoints(custom_epo, security=False, debug=False):
    """ A single method to add all endpoints """

    # ####################################
    # # HELLO WORLD endpoint...
    # @rest.resource('/')
    # # @rest.resource('/', '/hello')
    # class Hello(Resource):
    #     """ Example with no authentication """
    #     def get(self):
    #         return "Hello world", 200
    # logger.debug("Base endpoint: Hello world!")

    ####################################
    # Verify configuration
    resources = MyConfigs().rest()

    ####################################
    # Basic configuration (simple): from example class
    if len(resources) < 1:
        logger.info("No file configuration found (or no section inside)")
        from .resources import exampleservices as mymodule
        custom_epo.many_from_module(mymodule)
    # Advanced configuration (cleaner): from your module and .ini
    else:
        logger.info("Using resources found in configuration")

        for myclass, instance, endpoint, endkey in resources:
            # Load each resource
            custom_epo.create_single(myclass, endpoint, endkey)

    ####################################
    # Verify functions on the API server
    if security:
        from .resources import endpoints
        custom_epo.many_from_module(endpoints)
    else:
        from .resources.endpoints import Status
        custom_epo.create_many({'status': Status})

    ####################################
    # Extra endpoints?

    # #EXAMPLE:
    # from .resources import profiles
    # custom_epo.many_from_module(profiles)

    ####################################
    # The end
    return custom_epo
