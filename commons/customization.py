# -*- coding: utf-8 -*-

"""
Customization based on configuration 'blueprint' files
"""

import os
from collections import OrderedDict
# from jinja2._compat import iteritems
from . import (
    JSON_EXT, json, CORE_DIR, USER_CUSTOM_DIR,
    PATH, CONFIG_PATH, BLUEPRINT_KEY,  # CONFIG_DIR,
    API_URL, BASE_URLS,
)
from attr import (
    s as AttributedModel,
    ib as attribute,
)
from .meta import Meta
from .swagger import swaggerish
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
    uris = attribute(default=[])
    tags = attribute(default=[])


########################
# Customization on the table
########################

class Customizer(object):
    """
    CUSTOMIZE BACKEND: Read all of available configurations
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

        # ##################
        # # # TODO: mix default and custom configuration

        ##################
        # DEBUG
        pretty_print(custom_config)

        ##################
        # # FRONTEND?
        # custom_config['frameworks'] = \
        #     self.load_json(CONFIG_PATH, "", "frameworks")
        # auth = custom_config['variables']['containers']['authentication']

        ##################
        # Walk swagger directories custom and base
        self._endpoints = []
        swagger_dirs = []

        for basedir in [CORE_DIR, USER_CUSTOM_DIR]:

            current_dir = os.path.join(CONFIG_PATH, basedir)
            # log.debug("Looking into %s" % current_dir)

            # TODO: move this block into a function/method
            for endpoint in os.listdir(current_dir):
                log.info("Found endpoint %s" % endpoint)

                # FILE specs.json
                # load configuration and find file and class
                endpoint_dir = os.path.join(CONFIG_PATH, basedir, endpoint)
                conf = self.load_json('specs', endpoint_dir, skip_error=True)
                if conf is None:
                    continue
                elif 'class' not in conf:
                    raise ValueError("No 'class' in '%s' specs" % endpoint)

                # VERIFY IF AT LEAST ONE YAML FILE IS PRESENT
                # glob(*yaml)

                current = self.load_endpoint(endpoint, basedir, package, conf)
                if current.exists:
                    # Add endpoint to REST mapping
                    self._endpoints.append(current)
                    # Add current directory to YAML search for swagger def
                    swagger_dirs.append(endpoint_dir)
                else:
                    # raise AttributeError("Endpoint '%s' missing" % endpoint)
                    pass

        print("UHM", swagger_dirs, self._endpoints)
        exit(1)

        ##################

        # TODO: Write some swagger complete definitions

        # TODO: Swagger endpoints read definition for the first time
        swaggerish(package, dirs=swagger_dirs)
        print("SWAGGER COMPLETED")
        exit(1)

        # TODO: add endpoints to custom configuration to be saved

        # Save in memory all of the configurations
        from commons.globals import mem
        mem.custom_config = custom_config

    def read_complex_config(self, configfile):
        """ A more complex configuration is available in JSON format """
        content = {}
        with open(configfile) as fp:
            content = json.load(fp)
        return content

    def load_endpoint(self, default_uri, dir_name, package_name, conf):

        endpoint = EndpointElements()
        file_name = conf.get('file', default_uri)
        class_name = conf.get('class')
        name = '%s.%s.%s.%s' % (package_name, 'resources', dir_name, file_name)
        module = self._meta.get_module_from_string(name)

        if module is None:
            log.warning("Could not find python module '%s'..." % file_name)
            return endpoint

        #####################
        for dependency in conf.get('depends_on', []):
            if not getattr(module, dependency, False):
                log.warning("Skip %s: unmet %s" % (default_uri, dependency))
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

        #####################
        # MAPPING
        endpoint.uris = []  # attrs bug?

        # Set default, if no mappings defined
        mappings = conf.get('mapping', [])
        if len(mappings) < 1:
            mappings.append({'uri': default_uri})

        for mapping in mappings:

            pretty_print(mapping)
            uri = mapping.get('uri', None)
            if uri is None:
                raise AttributeError("Missing uri in mapping")

            # BUILD URI
            base = mapping.get('base_uri', API_URL)
            if base not in BASE_URLS:
                log.warning("Invalid base %s" % base)
                base = API_URL
            base = base.strip('/')

            # KEY NAME AND TYPE - for clarity
            key_name = ''
            mykey = mapping.get('id_name', None)
            mytype = mapping.get('id_type', 'string')
            if mykey is not None and mytype is not None:
                key_name = '/<%s:%s>' % (mytype, mykey)

            endpoint.uris.append('/%s/%s%s' % (base, uri, key_name))

            # AUTHENTICATION
            # ?

        #####################
        endpoint.tags = conf.get('labels', [])
        # pretty_print(endpoint)
        return endpoint

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
        log.error("Failed to read JSON from '%s'%s" % (filepath, error))

        if skip_error:
            return None
        else:
            exit(1)

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
