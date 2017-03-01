# -*- coding: utf-8 -*-

"""
a Farm: How to create endpoints into REST service.
"""

# from __future__ import absolute_import
# from restapi.utils.meta import Meta
from restapi.utils.logs import get_logger

log = get_logger(__name__)


class EndpointsFarmer(object):
    """ Handling endpoints creation"""

    rest_api = None

    def __init__(self, Api):
        super(EndpointsFarmer, self).__init__()
        # Init Restful plugin
        self.rest_api = Api(catch_all_404s=True)

    def add(self, resource):
        """ Adding a single restpoint from a Resource Class """

        from ..auth import authentication

        # Apply authentication: if required from yaml configuration
        # Done per each method
        for method, attributes in resource.custom['methods'].items():

            # If auth has some role, they have been validated
            # and authentication has been requested
            # if len(attributes.auth) < 1:
            #     continue
            # else:
            #     roles = attributes.auth

            roles = attributes.auth
            if roles is None:
                continue

            # Programmatically applying the authentication decorator
            # TODO: should this be moved to Meta class?
            # there is another similar piece of code in swagger.py
            original = getattr(resource.cls, method)
            decorated = authentication.authorization_required(
                original, roles=roles, from_swagger=True)
            setattr(resource.cls, method, decorated)
            log.very_verbose("Auth on %s.%s for %s"
                             % (resource.cls.__name__, method, roles))

        urls = [uri for _, uri in resource.uris.items()]

        # Create the restful resource with it;
        # this method is from RESTful plugin
        self.rest_api.add_resource(resource.cls, *urls)
        log.verbose("Map '%s' to %s", resource.cls.__name__, urls)

    # def create_single(self, resource, endpoints, endkey):
    #     """ Adding a single restpoint from a Resource Class """

    #     urls = []

    #     for endpoint in endpoints:

    #         address = resource.base_url + '/' + endpoint
    #         log.debug(
    #             "Mapping '%s' res to '%s'", resource.__name__, address)
    #         # Normal endpoint, e.g. /api/foo
    #         urls.append(address)
    #         # Special endpoint, e.g. /api/foo/:endkey
    #         if endkey is not None:
    #             newaddress = address + '/<' + endkey + '>'
    #             urls.append(newaddress)
    #             log.debug(
    #                 "Mapping '%s' to '%s'", resource.__name__, newaddress)

    #     # Create the restful resource with it
    #     self.rest_api.add_resource(resource, *urls)

    # def create_many(self, resources, custom_attributes=None):
    #     """ Automatic creation from an array of resources """

    #     # For each RESTful resource i receive
    #     for name, resource in resources.items():
    #         endpoint, endkey, endtype = resource().get_endpoint()

    #         endpoint_id = None
    #         if endkey is not None and endtype is not None:
    #             endpoint_id = endtype + ':' + endkey

    #         if custom_attributes is not None:
    #             for key, value in custom_attributes.items():
    #                 setattr(resource, key, value)

    #         self.create_single(resource, [endpoint], endpoint_id)

    # def many_from_module(self, module, custom_attributes=None):
    #     """ Automatic creation of endpoint from specified resources """

    #     resources = Meta().get_new_classes_from_module(module)
    #     # Init restful plugin
    #     if len(resources) > 0:
    #         self.create_many(resources, custom_attributes=custom_attributes)
