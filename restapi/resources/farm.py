# -*- coding: utf-8 -*-

"""
a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import
from .. import myself, lic, get_logger
from commons.meta import Meta

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class EndpointsFarmer(object):
    """ Handling endpoints creation"""

    rest_api = None

    def __init__(self, Api):
        super(EndpointsFarmer, self).__init__()
        # Init Restful plugin
        self.rest_api = Api(catch_all_404s=True)

    def create_single(self, resource, endpoints, endkey):
        """ Adding a single restpoint from a Resource Class """

        urls = []

        for endpoint in endpoints:
            address = resource.base_url + '/' + endpoint
            logger.debug(
                "Mapping '%s' res to '%s'", resource.__name__, address)
            # Normal endpoint, e.g. /api/foo
            urls.append(address)
            # Special endpoint, e.g. /api/foo/:endkey
            if endkey is not None:
                urls.append(address + '/<' + endkey + '>')

        # Create the restful resource with it
        self.rest_api.add_resource(resource, *urls)

    def create_many(self, resources):
        """ Automatic creation from an array of resources """
        # For each RESTful resource i receive
        for resource in resources:
            endpoint, endkey = resource().get_endpoint()
            self.create_single(resource, [endpoint], endkey)

    def many_from_module(self, module):
        """ Automatic creation of endpoint from specified resources """

        resources = Meta().get_new_classes_from_module(module)
        # Init restful plugin
        if len(resources) > 0:
            self.create_many(resources)
