# -*- coding: utf-8 -*-

"""
Integrating swagger in automatic ways.
Original source was:
https://raw.githubusercontent.com/gangverk/flask-swagger/master/flask_swagger.py

"""

from __future__ import absolute_import

import re
import os
# import inspect
# from collections import defaultdict
# from . import BASE_URLS, STATIC_URL, CORE_DIR, USER_CUSTOM_DIR, json
from attr import s as AttributedModel, ib as attribute
from .formats.yaml import load_yaml_file, YAML_EXT  # , yaml
from . import CORE_DIR, USER_CUSTOM_DIR

from .logs import get_logger  # , pretty_print

log = get_logger(__name__)
JSON_APPLICATION = 'application/json'


class BeSwagger(object):
    """Swagger class in our own way:

    Fewer methods than the original swagger reading,
    also more control and closer to the original swagger.
    """

    def __init__(self, endpoints):
        self._endpoints = endpoints
        self._paths = {}
        # The complete set of query parameters for all classes
        self._qparams = {}

    def read_my_swagger(self, file, method, endpoint):

        ################################
        # NOTE: the file reading here is cached
        # you can read it multiple times with no overload
        mapping = load_yaml_file(file)

        # content has to be a dictionary
        if not isinstance(mapping, dict):
            raise TypeError("Wrong method ")

        # read common
        commons = mapping.pop('common', {})

        # Check if there is at least one except for common
        if len(mapping) < 1:
            raise ValueError("No definition found inside: %s " % file)

        ################################
        # Using 'attrs': a way to save external attributes

        # Definition
        @AttributedModel
        class ExtraAttributes(object):
            auth = attribute(default=[])
            publish = attribute(default=True)
            whatever = attribute(default=None)

        # Instance
        extra = ExtraAttributes()

        ################################
        # Specs should contain only labels written in spec before

        pattern = re.compile(r'\<([^\>]+)\>')

        for label, specs in mapping.items():

            if label not in endpoint.uris:
                raise KeyError(
                    "Invalid label '%s' found.\nAvailable labels: %s"
                    % (label, list(endpoint.uris.keys())))
            uri = endpoint.uris[label]

            ################################
            # add common elements to all specs
            for key, value in commons.items():
                if key not in specs:
                    specs[key] = value

            ################################
            # Separate external definitions

            # Find any custom part which is not swagger definition
            custom = specs.pop('custom', {})

            # Publish the specs on the final Swagger JSON
            # Default is to do it if not otherwise specified
            extra.publish = custom.get('publish', True)

            # Authentication
            if custom.get('authentication', False):

                # TODO: get the default normal and admin user from 'auth'

                # If enabled, at least the base role should be present
                # roles = custom.get('authorized', ['normal_user'])
                roles = custom.get('authorized', [])

                for role in roles:

                    # TODO: create a method inside 'auth' to check roles

                    extra.auth = roles
            else:
                extra.auth = None

            # Other things that could be saved into 'custom' subset?

            ###########################
            # TODO: strip the uri of the parameter
            # and add it to 'parameters'
            newuri = uri[:]  # create a copy
            if 'parameters' not in specs:
                specs['parameters'] = []

            for parameter in pattern.findall(uri):

                # create parameters
                x = parameter.split(':')
                xlen = len(x)
                paramtype = 'string'

                if xlen == 1:
                    paramname = x[0]
                elif xlen == 2:
                    paramtype = x[0]
                    paramname = x[1]

                # TO FIX: complete for all types
                # http://swagger.io/specification/#data-types-12
                if paramtype == 'int':
                    paramtype = 'number'
                if paramtype == 'path':
                    paramtype = 'string'

                path_parameter = {
                    'name': paramname, 'type': paramtype,
                    'in': 'path', 'required': True
                }
                if paramname in endpoint.ids:
                    path_parameter['description'] = endpoint.ids[paramname]

                specs['parameters'].append(path_parameter)

                # replace in a new uri
                newuri = newuri.replace('<%s>' % parameter, '{%s}' % paramname)

            ##################
            # Skip what the developers does not want to be public in swagger
            if not extra.publish:
                continue

            # cycle parameters and add them to the endpoint class
            query_params = []
            for param in specs['parameters']:
                # handle parameters in URI for Flask
                if param['in'] == 'query':
                    query_params.append(param)

            if len(query_params) > 0:
                self.query_parameters(
                    endpoint.cls, method=method, uri=uri, params=query_params)

            # Swagger does not like empty arrays
            if len(specs['parameters']) < 1:
                specs.pop('parameters')

            # Handle global tags
            if 'tags' not in specs and len(endpoint.tags) > 0:
                specs['tags'] = []
            for tag in endpoint.tags:
                if tag not in specs['tags']:
                    specs['tags'].append(tag)

            ##################
            # NOTE: whatever is left inside 'specs' will be
            # passed later on to Swagger Validator...

            # Save definition for publishing
            if newuri not in self._paths:
                self._paths[newuri] = {}
            self._paths[newuri][method] = specs
            log.verbose("Built definition '%s:%s'" % (method.upper(), newuri))

        endpoint.custom[method] = extra
        return endpoint

    def query_parameters(self, cls, method, uri, params):
        """
        apply decorator to endpoint for query parameters
        # self._params[classname][URI][method][name]
        """

        clsname = cls.__name__
        if clsname not in self._qparams:
            self._qparams[clsname] = {}
        if uri not in self._qparams[clsname]:
            self._qparams[clsname][uri] = {}
        if method not in self._qparams[clsname][uri]:
            self._qparams[clsname][uri][method] = {}

        for param in params:
            name = param['name']
            if name not in self._qparams[clsname][uri][method]:
                self._qparams[clsname][uri][method][name] = param

    def swaggerish(self):
        """
        Go through all endpoints configured by the current development.

        Provide the minimum required data according to swagger specs.
        """

        # A template base
        output = {
            "swagger": "2.0",
            "info": {
                "version": "0.0.1",
                "title": "Your application name",
            },
            "schemes": [
                "http"
            ],
            "basePath": "/",
            # "host": "localhost:8080",
        }

        """
        SECURITY
        {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization"
        }
        # IN EVERY METHOD:
        parameters:
          - name: authorization
            in: header
            type: string
            required: true
        """

        # Set existing values
        from commons.globals import mem
        proj = mem.custom_config['project']
        if 'version' in proj:
            output['info']['version'] = proj['version']
        if 'title' in proj:
            output['info']['title'] = proj['title']

        for key, endpoint in enumerate(self._endpoints):
            endpoint.custom = {}
            for method, file in endpoint.methods.items():
                # add the custom part to the endpoint
                self._endpoints[key] = \
                    self.read_my_swagger(file, method, endpoint)

        ###################
        # Save query parameters globally
        from commons.globals import mem
        mem.query_params = self._qparams

        ###################
        output['definitions'] = self.read_definitions()
        output['consumes'] = [JSON_APPLICATION]
        output['produces'] = [JSON_APPLICATION]
        output['paths'] = self._paths

        ###################
        tags = []
        for tag, desc in mem.custom_config['tags'].items():
            tags.append({'name': tag, 'description': desc})
        output['tags'] = tags

        return output

    def read_definitions(self, filename='swagger'):
        """ Read definitions from base/custom yaml files """

        models_dir = os.path.join(__package__, 'models')

        # BASE definitions
        file = '%s.%s' % (filename, YAML_EXT)
        path = os.path.join(models_dir, CORE_DIR, file)
        data = load_yaml_file(path)

        # CUSTOM definitions
        # They may override existing ones
        file = '%s.%s' % (filename, YAML_EXT)
        path = os.path.join(models_dir, USER_CUSTOM_DIR, file)
        override = load_yaml_file(path, skip_error=True)
        if override is not None and isinstance(override, dict):
            for key, value in override.items():
                data[key] = value

        return data

    @staticmethod
    def validation(swag_dict):
        """
        Based on YELP library,
        verify the current definition on the open standard
        """

        if len(swag_dict['paths']) < 1:
            raise AttributeError("Swagger 'paths' definition is empty")
        # else:
        #     from commons.logs import pretty_print
        #     pretty_print(swag_dict)

        from bravado_core.spec import Spec

        try:
            from commons import original_json
            # Fix jsonschema validation problem
            # expected string or bytes-like object
            # http://j.mp/2hEquZy
            swag_dict = original_json.loads(original_json.dumps(swag_dict))
            # write it down
            with open('/tmp/test.json', 'w') as f:
                original_json.dump(swag_dict, f)
        except Exception as e:
            raise e
            log.warning("Failed to json fix the swagger definition")

        bravado_config = {
            'validate_swagger_spec': True,
            'validate_requests': False,
            'validate_responses': False,
            'use_models': False,
        }

        try:
            Spec.from_dict(swag_dict, config=bravado_config)
            log.info("Swagger configuration is validated")
        except Exception as e:
            # raise e
            error = str(e).split('\n')[0]
            log.error("Failed to validate:\n%s\n" % error)
            return False

        return True
