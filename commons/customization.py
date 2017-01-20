# -*- coding: utf-8 -*-

"""
Customization based on configuration 'blueprint' files
"""

from __future__ import absolute_import

import os
import re
import glob
from collections import OrderedDict
from . import (
    JSON_EXT, json, CORE_DIR, USER_CUSTOM_DIR, DEFAULTS_PATH,
    PATH, CONFIG_PATH, BLUEPRINT_KEY, API_URL, BASE_URLS,
)
from .meta import Meta
from .formats.yaml import YAML_EXT, load_yaml_file
from .swagger import BeSwagger
from .attrs.api import EndpointElements, ExtraAttributes
# from .globals import mem

from .logs import get_logger

log = get_logger(__name__)


########################
# Customization on the table
########################

class Customizer(object):
    """
    Customize your BACKEND:
    Read all of available configurations and definitions.

    """
    def __init__(self, package):

        # Some initialization
        self._current_package = package
        self._endpoints = []  # TO FIX: should not be a list, but a dictionary
        self._definitions = {}
        self._configurations = {}
        self._query_params = {}
        self._meta = Meta()

        # Do things
        self.do_config()
        self.do_schema()
        self.find_endpoints()
        self.do_swagger()

    def do_config(self):
        ##################
        # Reading configuration

        # Find out what is the active blueprint
        bp_holder = self.load_json(BLUEPRINT_KEY, PATH, CONFIG_PATH)
        blueprint = bp_holder[BLUEPRINT_KEY]

        # Read the custom configuration from the active blueprint file
        custom_config = self.load_json(blueprint, PATH, CONFIG_PATH)
        custom_config[BLUEPRINT_KEY] = blueprint

        # Read default configuration
        defaults = self.load_json(BLUEPRINT_KEY, DEFAULTS_PATH, CONFIG_PATH)
        if len(defaults) < 0:
            raise ValueError("Missing defaults for server configuration!")

        # Mix default and custom configuration
        # We go deep into two levels down of dictionaries
        for key, elements in defaults.items():
            if key not in custom_config:
                custom_config[key] = {}
            for label, element in elements.items():
                if label not in custom_config[key]:
                    custom_config[key][label] = element

        # # FRONTEND?
        # TO FIX: see with @mdantonio what to do here
        # custom_config['frameworks'] = \
        #     self.load_json(CONFIG_PATH, "", "frameworks")
        # auth = custom_config['variables']['containers']['authentication']

        # Save in memory all of the current configuration
        self._configurations = custom_config

    def do_schema(self):
        """ Schemas exposing, if requested """

        name = '%s.%s.%s.%s' % (
            self._current_package, 'resources', 'rest', 'schema')
        module = self._meta.get_module_from_string(name)
        schema_class = getattr(module, 'RecoverSchema')

        self._schema_endpoint = EndpointElements(
            cls=schema_class,
            exists=True,
            custom={
                'methods': {
                    'get': ExtraAttributes(auth=None),
                    # WHY DOES POST REQUEST AUTHENTICATION
                    # 'post': ExtraAttributes(auth=None)
                }
            },
            methods={}
        )

        # TODO: find a way to map authentication
        # as in the original endpoint for the schema 'get' method

        # TODO: find a way to publish on swagger the schema
        # if endpoint is enabled to publish and the developer asks for it

    def find_endpoints(self):

        ##################
        # Walk swagger directories looking for endpoints

        # for base_dir in [CORE_DIR]:
        for base_dir in [CORE_DIR, USER_CUSTOM_DIR]:

            current_dir = os.path.join(CONFIG_PATH, base_dir)

            for ep in os.listdir(current_dir):

                endpoint_dir = os.path.join(CONFIG_PATH, base_dir, ep)
                if os.path.isfile(endpoint_dir):
                    log.debug(
                        "Expected a swagger conf folder, found a file (%s/%s)"
                        % (base_dir, ep)
                    )
                    continue
                current = self.lookup(
                    ep, self._current_package, base_dir, endpoint_dir)
                if current.exists:
                    # Add endpoint to REST mapping
                    self._endpoints.append(current)

    def do_swagger(self):

        # SWAGGER read endpoints definition
        swag = BeSwagger(self._endpoints, self)
        swag_dict = swag.swaggerish()

        # TODO: I should update internal endpoints from swagger
        self._endpoints = swag._endpoints[:]

        # SWAGGER validation
        if not swag.validation(swag_dict):
            raise AttributeError("Current swagger definition is invalid")

        self._definitions = swag_dict

    def lookup(self, endpoint, package, base_dir, endpoint_dir):

        log.verbose("Found endpoint dir: '%s'" % endpoint)

        # Find yaml files
        conf = None
        yaml_files = {}
        yaml_listing = os.path.join(endpoint_dir, "*.%s" % YAML_EXT)
        for file in glob.glob(yaml_listing):
            if file.endswith('specs.%s' % YAML_EXT):
                # load configuration and find file and class
                conf = load_yaml_file(file)
            else:
                # add file to be loaded from swagger extension
                p = re.compile(r'\/([^\.\/]+)\.' + YAML_EXT + '$')
                match = p.search(file)
                method = match.groups()[0]
                yaml_files[method] = file

        if len(yaml_files) < 1:
            raise Exception("%s: methods undefined" % endpoint)
        if conf is None or 'class' not in conf:
            raise ValueError("No 'class' defined for '%s'" % endpoint)

        current = self.load_endpoint(endpoint, base_dir, package, conf)
        current.methods = yaml_files
        return current

    def read_complex_config(self, configfile):
        """ A more complex configuration is available in JSON format """
        content = {}
        with open(configfile) as fp:
            content = json.load(fp)
        return content

    def load_endpoint(self, default_uri, dir_name, package_name, conf):

        endpoint = EndpointElements(custom={})

        #####################
        # Load the endpoint class defined in the YAML file
        file_name = conf.pop('file', default_uri)
        class_name = conf.pop('class')
        name = '%s.%s.%s.%s' % (package_name, 'resources', dir_name, file_name)
        module = self._meta.get_module_from_string(name)

        if module is None:
            log.warning("Could not find module %s in %s" % (name, file_name))
            # exit(1)
            return endpoint

        #####################
        # Check for dependecies and skip if missing
        for dependency in conf.pop('depends_on', []):
            if not getattr(module, dependency, False):
                log.verbose("Skip '%s': unmet %s" % (default_uri, dependency))
                return endpoint

        endpoint.cls = self._meta.get_class_from_string(class_name, module)
        if endpoint.cls is None:
            log.critical("Could not extract python class '%s'" % class_name)
            return endpoint
        else:
            endpoint.exists = True

        # Is this a base or a custom class?
        endpoint.isbase = dir_name == 'base'

        # DEPRECATED
        # endpoint.instance = endpoint.cls()

        # Global tags
        # to be applied to all methods
        endpoint.tags = conf.pop('labels', [])

        # base URI
        base = conf.pop('baseuri', API_URL)
        if base not in BASE_URLS:
            log.warning("Invalid base %s" % base)
            base = API_URL
        base = base.strip('/')

        #####################
        # MAPPING
        schema = conf.pop('schema', {})
        mappings = conf.pop('mapping', [])
        if len(mappings) < 1:
            raise KeyError("Missing 'mapping' section")

        endpoint.uris = {}  # attrs python lib bug?
        endpoint.custom['schema'] = {
            'expose': schema.get('expose', False),
            'publish': {}
        }
        for label, uri in mappings.items():

            # BUILD URI
            total_uri = '/%s%s' % (base, uri)
            endpoint.uris[label] = total_uri

            # If SCHEMA requested add uri + '/schema' to schema.py
            if endpoint.custom['schema']['expose']:
                p = hex(id(endpoint.cls))
                self._schema_endpoint.uris[label + p] = total_uri + '/schema'
                endpoint.custom['schema']['publish'][label] = \
                    schema.get('publish', False)

        # Description for path parameters
        endpoint.ids = conf.pop('ids', {})

        # Check if something strange is still in configuration
        if len(conf) > 0:
            raise KeyError("Unwanted keys: %s" % list(conf.keys()))

        return endpoint

    # TODO: move json things into commons/formats/json.py
    @staticmethod
    def load_json(file, path, config_root='', skip_error=False, retfile=False):
        """
        Trying to avoid all the verbose error from commentjson
        """

        filepath = os.path.join(config_root, path, file + "." + JSON_EXT)
        if retfile:
            return filepath
        log.debug("Reading file %s" % filepath)

        # Use also the original library
        import json as original_json
        error = None

        # JSON load from this file
        if os.path.exists(filepath):
            with open(filepath) as fh:
                try:
                    return json.load(fh, object_pairs_hook=OrderedDict)
                except json.commentjson.JSONLibraryException as e:
                    error = e
                except original_json.decoder.JSONDecodeError as e:
                    error = e
                except Exception as e:
                    error = e
        else:
            error = 'File does not exist'

        if error is not None:
            # Make sense of the JSON parser error...
            for line in str(error).split('\n')[::-1]:
                if line.strip() != '':
                    error = line
                    break
            error = ':\n%s' % error
        else:
            error = ''
        message = "Failed to read JSON from '%s'%s" % (filepath, error)

        if skip_error:
            log.error(message)
            return None
        else:
            raise Exception(message)
