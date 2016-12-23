# -*- coding: utf-8 -*-

"""
App specifications
"""

from __future__ import division
from . import myself, lic
from commons.logs import get_logger
from flask_restful import Api as RestFulApi
from .resources.farm import EndpointsFarmer
# from .config import MyConfigs
from commons.customization import Customizer

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
logger.debug(
    "Restful classes to create endpoints: [%s, %s]" % (Api, EndpointsFarmer))


def create_endpoints(custom_epo, security=False, debug=False):
    """ A single method to add all endpoints """

    # HELLO WORLD endpoint:
    #
    # ####################################
    # @rest.resource('/')
    # # @rest.resource('/', '/hello')
    # class Hello(Resource):
    #     """ Example with no authentication """
    #     def get(self):
    #         return "Hello world", 200
    # logger.debug("Base endpoint: Hello world!")

    ####################################
    # Verify configuration
    customization = Customizer()
    # resources = MyConfigs().rest()

    resources = customization.endpoints()

    ####################################
    # Basic configuration (simple): from example class
    if len(resources) < 1:
        logger.warning("No custom endpoints found!")
        from .resources import exampleservices as mymodule
        custom_epo.many_from_module(mymodule)
        logger.debug("Loaded example class instead")
    # Advanced configuration (cleaner): from swagger definition
    else:
        logger.info("Using resources defined with Swagger")
        for myclass, instance, endpoint, endkey in resources:
            # Load each resource
            custom_epo.create_single(myclass, endpoint, endkey)

    exit(0)

    ####################################
# TODO: TO BE REMOVED (with the related code)
    # Define the base endpoints by injecting into the service

    # Give me something to distinguish these endpoints classes from custom
    extrattrs = {'_is_base': True}

    if security:
        from .resources import endpoints
        custom_epo.many_from_module(endpoints, custom_attributes=extrattrs)
    else:
        from .resources.endpoints import Status
        custom_epo.create_many({'status': Status}, custom_attributes=extrattrs)

    ####################################
    # The end
    return custom_epo
