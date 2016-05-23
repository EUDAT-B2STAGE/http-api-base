# -*- coding: utf-8 -*-

""" How to create endpoints into REST service """

from .. import get_logger
from ..meta import Meta

logger = get_logger(__name__)


class Endpoints(object):
    """ Handling endpoints creation"""

    rest_api = None

    def __init__(self, api):
        super(Endpoints, self).__init__()
        self.rest_api = api

    def create_single(self, resource, endpoints, endkey):
        """ Adding a single restpoint from a Resource Class """

        urls = []

        for endpoint in endpoints:
            print(endpoint, resource.base_url)
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
