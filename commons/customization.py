# -*- coding: utf-8 -*-

"""
Customization based on configuration 'blueprint' files
"""

import os
import glob
from collections import OrderedDict
# from jinja2._compat import iteritems
from . import (
    JSON_EXT, json, CORE_DIR, USER_CUSTOM_DIR,
    PATH, CONFIG_PATH, BLUEPRINT_KEY,
    # CONFIG_DIR,
)
from attr import (
    s as AttributedModel,
    ib as attribute,
)
from .meta import Meta
from .logs import get_logger, pretty_print

logger = get_logger(__name__)


########################
# Elements for endpoint configuration
########################
@AttributedModel
class EndpointElements(object):
    exists = attribute(default=False)  # bool
    cls = attribute(default=None)
    instance = attribute(default=None)
    uri = attribute(default=None)
    key_name = attribute(default=None)


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
        #     logger.debug("Defaults:\n%s" % defaults)

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
        swagger_endpoints = []

        # CONFIG_PATH + whatever?
        for dir in [CORE_DIR, USER_CUSTOM_DIR]:

            current_dir = os.path.join(CONFIG_PATH, dir)
            # logger.debug("Looking into %s" % current_dir)

            # TODO: move this block into a function/method
            for element in glob.glob(os.path.join(current_dir, '*')):

                endpoint = element.replace(current_dir, '').strip('/')
                logger.info("Found endpoint %s" % endpoint)

                # load configuration and find file and class
                endpoint_dir = os.path.join(dir, endpoint)
                conf = self.load_json(
                    'specs', endpoint_dir, CONFIG_PATH, skip_error=True)
                if conf is None:
                    continue
                if 'class' not in conf:
                    raise ValueError(
                        "Missing 'class' attribute in '%s' specs" % endpoint)

                current = self.load_endpoint(
                    endpoint,
                    conf.get('file', endpoint),
                    conf.get('class'),
                    dir,
                    package,
                    conf.get('depends_on', None),
                    conf.get('id_name', None),
                    conf.get('id_type', 'string')
                )
                if current.exists:
                    # Add endpoint
                    self._endpoints.append(current)
                    # Add to list of yaml files
                    swagger_endpoints.append(element)
                else:
                    # raise AttributeError("Endpoint '%s' missing" % endpoint)
                    pass

        ##################

        # TODO: Write some swagger complete definitions

        # TODO: Swagger endpoints read definition for the first time
        from .swagger import swaggerish
        swaggerish(package, dirs=swagger_endpoints)
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

    def load_endpoint(self, uri, file_name, class_name,
                      dir_name, package_name, depends=None,
                      mykey=None, mytype=None):

        endpoint = EndpointElements()

        module = self._meta.get_module_from_string(
            '%s.%s.%s.%s' % (package_name, 'resources', dir_name, file_name)
        )
        if module is None:
            logger.warning("Could not find python module '%s'..." % file_name)
            return endpoint

        if depends is not None:
            if not getattr(module, depends, False):
                logger.warning("Skipping %s" % uri)
                return endpoint

        endpoint.cls = self._meta.get_class_from_string(class_name, module)
        if endpoint.cls is None:
            logger.critical("Could not find python class '%s'..." % class_name)
            return endpoint
        else:
            endpoint.exists = True

        # Get the best endpoint comparing inside against configuration
        endpoint.instance = endpoint.cls()

        reference, endkey, endtype = endpoint.instance.get_endpoint()

        # Decide URI between how the folder is and the one forced
        if reference is not None:
            # TO FIX: this mode should be remove
            logger.warning("Something to check here")
            print("\n\n\nTEST URI %s\n\n\n" % reference)
            endpoint.uri = reference
        else:
            endpoint.uri = uri

        endpoint.key_name = None
        if endkey is not None and endtype is not None:
            endpoint.key_name = endtype + ':' + endkey
        if mykey is not None and mytype is not None:
            if endpoint.key_name is not None:
                logger.warning("Double configuration of endpoint key")
            endpoint.key_name = mytype + ':' + mykey

        # pretty_print(endpoint)
        return endpoint

    @staticmethod
    def load_json(file, path, config_root, skip_error=False, retfile=False):
        """
        Trying to avoid all the verbose error from commentjson
        """

        filepath = os.path.join(config_root, path, file + "." + JSON_EXT)
        if retfile:
            return filepath
        logger.debug("Reading file %s" % filepath)

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
        logger.error("Failed to read JSON from '%s'%s" % (filepath, error))

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
