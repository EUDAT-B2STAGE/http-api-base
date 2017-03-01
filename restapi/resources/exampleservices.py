# -*- coding: utf-8 -*-

"""
Mock Resources as Example

# TO FIX: more like the swagger new way, or remove it.
"""

# In case you do not know how API endpoints usually looks,
# see some examples here to take inspiration
# https://parse.com/docs/rest/guide

from __future__ import absolute_import

# from . import decorators as decorate
from .base import ExtendedApiResource
# from ..confs import config
# from ..auth import authentication
from restapi.utils.logs import get_logger

log = get_logger(__name__)


#####################################
# 1) Simplest example
class FooOne(ExtendedApiResource):
    """ Empty example for mock service with no :myid """

    # @decorate.apimethod
    def get(self):
        return 'Hello world!'
    # Works with request(s) to:
    # GET /api/foo


# #####################################
# # 2) Little more complex example
# @decorate.enable_endpoint_identifier('identifier')
# class FooTwo(ExtendedApiResource):
#     """ Example with use of myid """

#     # Specify a different endpoint
#     endpoint = 'another/path'

#     @decorate.apimethod
#     def get(self, identifier=None):
#         log.debug("Using different endpoint")
#         key = 'hello'

#         # I want to check if /api/another/path/identifier is empty
#         if identifier is not None:
#             key += ' ' + identifier
#             log.info("Using data key '%s'" % identifier)

#         return {key: 'new endpoint'}
#     # Works with requests to:
#     # GET /api/another/path
#     # GET /api/another/path/:identifier

# # NOTE: this endpoint will crash if you DISABLE SECURITY on this app
#     @decorate.apimethod
#     @authentication.authorization_required(roles=[config.ROLE_USER])
# # NOTE: this endpoint will crash if you DISABLE SECURITY on this app
#     def post(self, identifier=None):
#         """ I do nothing """
#         pass
#     # Works with requests to:
#     # POST /api/another/path (respond with null)


# #####################################
# # 3) Example with parameters
# class FooThree(ExtendedApiResource):
#     """
#     Example with parameters.
#     Add as many parameter in a decorator stack on top of the method.

#     BEWARE: the decorator 'apimethod' has to be the innermost in the stack
#     OTHERWISE NO PARAMETERS WILL BE SEEN
#     """

#     # Adding parameter with decorator
#     @decorate.add_endpoint_parameter('myarg')
#     @decorate.apimethod
#     def get(self):
#         log.debug("Received args %s" % self._args)
#         return self._args
#     # Works with requests to:
#     # GET /api/another/path?myarg=a

#     # Adding parameters with decorator in different ways
#     @decorate.add_endpoint_parameter('arg1', str)
#     @decorate.add_endpoint_parameter('arg2', ptype=int)
#     @decorate.add_endpoint_parameter(name='arg3', ptype=str)
#     @decorate.apimethod
#     def post(self):
#         log.debug("Received args %s" % self._args)
#         return self.force_response(errors={'something': 'went wrong'})
#     # Works with requests to:
#     # POST /api/another/path?arg2=3&arg3=test
