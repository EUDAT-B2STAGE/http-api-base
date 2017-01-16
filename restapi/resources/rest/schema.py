# -*- coding: utf-8 -*-

"""
Add schema endpoint if you have models to expose
"""

from __future__ import absolute_import

from .definition import EndpointResource
from commons.logs import get_logger  # , pretty_print

log = get_logger(__name__)


class RecoverSchema(EndpointResource):

    def get(self):
        """ Expose schemas for UIs automatic form building """

        # TO FIX: not from json but from query
        method = self.get_input(single_parameter='method', default='GET')
        out1 = self.get_endpoint_definition(
            key='parameters', is_schema_url=True, method=method)
        out2 = self.get_endpoint_custom_definition(
            key='parameters', is_schema_url=True, method=method)
        return "Hello"
