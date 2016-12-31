# -*- coding: utf-8 -*-

"""
Customization based on configuration 'blueprint' files
"""

from __future__ import absolute_import

import os
import re
import glob
from collections import OrderedDict
from attr import s as AttributedModel, ib as attribute
# from jinja2._compat import iteritems
from . import (
    JSON_EXT, json, CORE_DIR, USER_CUSTOM_DIR,
    PATH, CONFIG_PATH, BLUEPRINT_KEY, API_URL, BASE_URLS,
)
from .meta import Meta
from .formats.yaml import YAML_EXT, load_yaml_file
from .swagger import BeSwagger
from .globals import mem
from .logs import get_logger, pretty_print

log = get_logger(__name__)


########################
# Elements for endpoint configuration
########################
@AttributedModel
class EndpointElements(object):
    exists = attribute(default=False)  # bool
    cls = attribute(default=None)
    instance = attribute(default=None)
    uris = attribute(default={})
    methods = attribute(default=[])
    custom = attribute(default={})
    tags = attribute(default=[])


########################
# Customization on the table
########################

class Customizer(object):
    """
    Customize your BACKEND:
    Read all of available configurations and definitions.
    """
    def __init__(self, package):

        self._meta = Meta()

        ##################
        # # CUSTOM configuration
        # from Blueprint mounted directory
        bp_holder = self.load_json(BLUEPRINT_KEY, PATH, CONFIG_PATH)
        # pretty_print(bp_holder)
        blueprint = bp_holder[BLUEPRINT_KEY]
        custom_config = self.load_json(blueprint, PATH, CONFIG_PATH)
        custom_config[BLUEPRINT_KEY] = blueprint

        # ##################
        # # # DEFAULT configuration (NOT IMPLEMENTED YET)
        # # Add a value for all possibilities
        # defaults = self.load_json('defaults', CONFIG_DIR, __package__)
        # if len(defaults) > 0:
        #     log.debug("Defaults:\n%s" % defaults)

        # # TODO: mix default and custom configuration

        # ##################
        # # DEBUG
        # pretty_print(custom_config)

        ##################
        # # FRONTEND?
        # TO FIX: see with @mdantonio how to fix here
        # custom_config['frameworks'] = \
        #     self.load_json(CONFIG_PATH, "", "frameworks")
        # auth = custom_config['variables']['containers']['authentication']

        ##################
        # Walk swagger directories (both custom and base)
        endpoints = []

        for base_dir in [CORE_DIR, USER_CUSTOM_DIR]:

            current_dir = os.path.join(CONFIG_PATH, base_dir)

            for ep in os.listdir(current_dir):

                endpoint_dir = os.path.join(CONFIG_PATH, base_dir, ep)
                current = self.lookup(ep, package, base_dir, endpoint_dir)
                if current.exists:
                    # Add endpoint to REST mapping
                    endpoints.append(current)

        ##################

        # Save in memory all of the configuration
        mem.custom_config = custom_config

        # TODO: Write swagger complete definitions in base

        # [SWAGGER]: read endpoints definition
        # for the first time (at init time)
        swag = BeSwagger(endpoints)
        swag_dict = swag.swaggerish()

        # print("DEBUG")
        # pretty_print(swag_dict)
        # exit(1)
        # with open('/tmp/test.json', 'w') as fh:
        #     fh.write(swag_dict)

        # [SWAGGER]: validation
        if not swag.validation(swag_dict):
            raise AttributeError("Current swagger definition is invalid")

        # TODO: update mem configuration with swagger definition
        # TODO: add endpoints to custom configuration to be saved
        # mem.custom_config

        print("ARE ENDPOINTS USABLE NOW??")
        exit(1)
        pretty_print(endpoints)
        exit(0)
        self._endpoints = endpoints

        print("DEBUG")
        exit(1)

    def lookup(self, endpoint, package, base_dir, endpoint_dir):

        log.info("Found endpoint dir: '%s'" % endpoint)

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

        endpoint = EndpointElements()
        file_name = conf.pop('file', default_uri)
        class_name = conf.pop('class')
        name = '%s.%s.%s.%s' % (package_name, 'resources', dir_name, file_name)
        module = self._meta.get_module_from_string(name)

        if module is None:
            log.warning("Could not find python module '%s'..." % file_name)
            return endpoint

        #####################
        for dependency in conf.pop('depends_on', []):
            if not getattr(module, dependency, False):
                log.warning("Skip '%s': unmet %s" % (default_uri, dependency))
                return endpoint

        endpoint.cls = self._meta.get_class_from_string(class_name, module)
        if endpoint.cls is None:
            log.critical("Could not extract python class '%s'" % class_name)
            return endpoint
        else:
            endpoint.exists = True

        # Create the instance to recover all elements inside
        endpoint.instance = endpoint.cls()
        reference, endkey, endtype = endpoint.instance.get_endpoint()
        if reference is not None:
            # endpoint.default_uri = reference
            raise ValueError("DEPRECATED: URI reference %s in class %s"
                             % (reference, endpoint.cls))
        # if endkey is not None and endtype is not None:
        #     endpoint.key_name = endtype + ':' + endkey
        if endkey is not None or endtype is not None:
            raise ValueError("DEPRECATED: key/type in class %s" % endpoint.cls)

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
        mappings = conf.pop('mapping', [])
        if len(mappings) < 1:
            raise KeyError("Missing 'mapping' section")

        endpoint.uris = {}  # attrs bug?
        for label, uri in mappings.items():

            # BUILD URI
            total_uri = '/%s%s' % (base, uri)
            endpoint.uris[label] = total_uri

        # Check if something strange is still in configuration
        if len(conf) > 0:
            raise KeyError("Unwanted keys: %s" % list(conf.keys()))

        # pretty_print(endpoint)
        # exit(1)
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

    def endpoints(self):
        return self._endpoints

    # def read_config(self, configfile, case_sensitive=True):

    #     """
    #     A generic reader for 'ini' files via standard library
# NOTE: this method is UNUSED at the moment
# But it could become usefull for reading '.ini' files
    #     """

    #     sections = {}
    #     try:
    #         import configparser
    #     except:
    #         # python2
    #         import ConfigParser as configparser

    #     if case_sensitive:
    #         # Make sure configuration is case sensitive
    #         config = configparser.RawConfigParser()
    #         config.optionxform = str
    #     else:
    #         config = configparser.ConfigParser()

    #     # Read
    #     config.read(configfile)
    #     for section in config.sections():
    #         print(section)
    #         elements = {}
    #         for classname, endpoint in iteritems(dict(config.items(section))):
    #             print(classname, endpoint)
    #             elements[classname] = [endpoint]
    #         sections[str(section)] = elements

    #     return sections
