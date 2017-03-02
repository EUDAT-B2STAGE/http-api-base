# -*- coding: utf-8 -*-

"""
Add schema endpoint if you have models to expose
"""

from __future__ import absolute_import

from rapydo.core.rest.definition import EndpointResource
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class RecoverSchema(EndpointResource):

    def get(self, **kwargs):
        """ Expose schemas for UIs automatic form building """

        # TO FIX: not from json but from query
        method = self.get_input(single_parameter='method', default='POST')

        # schema_definition = self.get_endpoint_definition(
        #     key='parameters', is_schema_url=True, method=method)

        custom_definition = self.get_endpoint_custom_definition(
            method=method, is_schema_url=True)

        return self.force_response(custom_definition)
