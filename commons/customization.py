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
    PATH, CONFIG_PATH, CONFIG_DIR, BLUEPRINT_KEY,
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
    theclass = attribute(default=None)
    theinstance = attribute(default=None)
    uri = attribute(default=None)
    key_name = attribute(default=None)


########################
# Customization on the table
########################

class Customizer(object):
    """
    CUSTOMIZE BACKEND: Read all of available configurations
    """
    def __init__(self):

        self._meta = Meta()

        ##################
        # # DEFAULT configuration (NOT IMPLEMENTED YET)
        # Add a value for all possibilities
        defaults = self.load_json('defaults', CONFIG_DIR, __package__)
        if len(defaults) > 0:
            logger.debug("Defaults:\n%s" % defaults)

        ##################
        # # CUSTOM configuration
        # from Blueprint mounted directory
        bp_holder = self.load_json(BLUEPRINT_KEY, PATH, CONFIG_PATH)
        # pretty_print(bp_holder)
        blueprint = bp_holder[BLUEPRINT_KEY]
        custom_config = self.load_json(blueprint, PATH, CONFIG_PATH)
        custom_config[BLUEPRINT_KEY] = blueprint

        pretty_print(custom_config)

        ##################
        # # FRONTEND?
        # custom_config['frameworks'] = \
        #     self.load_json(CONFIG_PATH, "", "frameworks")
        # auth = custom_config['variables']['containers']['authentication']

        ##################
# TODO: walk swagger directories custom and base

        # CONFIG_PATH + whatever?
        for dir in [CORE_DIR, USER_CUSTOM_DIR]:

            current_dir = os.path.join(CONFIG_PATH, dir)
            logger.debug("Looking into %s" % current_dir)

            for element in glob.glob(os.path.join(current_dir, '*')):
                print("BASE or CUSTOM?", dir)

                endpoint = element.replace(current_dir, '').strip('/')
                logger.info("Found endpoint %s" % endpoint)

                # load configuration and find file and class
                endpoint_dir = os.path.join(dir, endpoint)
                conf = self.load_json('specs', endpoint_dir, CONFIG_PATH)
                pretty_print(conf)

                # myclass, instance, endpoint, endkey
                self.load_endpoint(conf['file'], conf['class'], dir, 'restapi')
                print("DEBUG")
                exit(1)

        ##################
        # TODO: add endpoints to custom configuration to be saved

        # Save in memory all of the configurations
        from commons.globals import mem
        mem.custom_config = custom_config

        ##################
        # Swagger endpoints
        self._endpoints = []
        return

    # def read_config(self, configfile, case_sensitive=True):

    #     """
    #     A generic reader for 'ini' files via standard library
# THIS METHOD IS UNUSED AT THE MOMENT
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

    def read_complex_config(self, configfile):
        """ A more complex configuration is available in JSON format """
        content = {}
        with open(configfile) as fp:
            content = json.load(fp)
        return content

    def load_endpoint(self, file_name, class_name, dir_name, package_name):

        endpoint = EndpointElements()
        module = self._meta.get_module_from_string(
            '%s.%s.%s.%s' % (package_name, 'resources', dir_name, file_name)
        )
        print("TEST", file_name, class_name, module)
        exit(1)

        # Skip what you cannot use
        if module is None:
            logger.warning("Could not find python module '%s'..." % file_name)
            return endpoint

        myclass = self._meta.get_class_from_string(class_name, module)
        # Again skip
        if myclass is None:
            return endpoint
        else:
            endpoint.exists = True
            logger.debug("REST! Found resource")

        # Get the best endpoint comparing inside against configuration
        endpoint.instance = myclass()

        reference, endkey, endtype = endpoint.instance.get_endpoint()
        endpoint.reference = reference

        endpoint.key_name = None
        if endkey is not None and endtype is not None:
            endpoint.key_name = endtype + ':' + endkey

        pretty_print(endpoint)
        exit(1)
        return endpoint

#     def single_rest(self, config_file):

#         meta = self._meta
#         resources = []
#         sections = {}

#         if not os.path.exists(config_file):
#             logger.warning("File '%s' does not exist! Skipping." % config_file)
#             return resources

#         #########################
#         # Read the configuration inside this init file

#         # JSON CASE
#         try:
#             sections = self.read_complex_config(config_file)
#         except:  # json.commentjson.JSONLibraryException:
#             logger.critical("Format error!\n" +
#                             "'%s' file is not in JSON format" % config_file)
#             exit(1)

#         if 'apis' not in sections:
#             logger.critical(
#                 "Section 'apis' not found in '%s' file" % config_file
#             )
#             exit(1)

#         #########################
#         # Use sections found: READING APIs MAPPING
#         for section, items in iteritems(sections['apis']):

#             logger.debug("Configuration read: {Section: " + section + "}")

#             module = meta.get_module_from_string(
# # TO FIX: PACKAGE should be a parameter from the server..
#                 __package__ + '.resources.custom.' + section)
#             # Skip what you cannot use
#             if module is None:
#                 logger.warning("Could not find module '%s'..." % section)
#                 continue

#             for classname, endpoints in iteritems(items):
#                 myclass = meta.get_class_from_string(classname, module)
#                 # Again skip
#                 if myclass is None:
#                     continue
#                 else:
#                     logger.debug("REST! Found resource: " +
#                                  section + '.' + classname)

#                 # Get the best endpoint comparing inside against configuration
#                 instance = myclass()

#                 oldendpoint, endkey, endtype = instance.get_endpoint()
#                 if len(endpoints) < 1:
#                     endpoints = [oldendpoint]

#                 endpoint_id = None
#                 if endkey is not None and endtype is not None:
#                     endpoint_id = endtype + ':' + endkey

#                 resources.append((myclass, instance, endpoints, endpoint_id))

#         return resources

    @staticmethod
    def load_json(file, path, config_root):
        """
        Trying to avoid all the verbose error from commentjson
        """

        filepath = os.path.join(config_root, path, file + "." + JSON_EXT)
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

        # Make sense of the JSON parser error...
        for line in str(error).split('\n')[::-1]:
            if line.strip() != '':
                error = line
                break
        logger.error("Failed to read JSON from '%s':\n%s" % (filepath, error))
        exit(1)

    def endpoints(self):
        return self._endpoints

    # def rest(self):
    #     """ REST endpoints as specified inside '.json' configuration file """

    #     files = []
    #     # logger.debug("Trying configurations from '%s' dir" % REST_CONFIG)
    #     # if os.path.exists(BLUEPRINT_FILE):
    #     #     with open(BLUEPRINT_FILE) as f:
    #     #         mydict = self.load_and_handle_json_exception(f)
    #     #         blueprint = mydict['blueprint']
    #     #         files.append(os.path.join(REST_CONFIG, blueprint + '.json'))
    #     # else:
    #     #     logger.critical("Missing a blueprint file: %s" % BLUEPRINT_FILE)
    #     logger.debug("Resources files: '%s'" % files)

    #     resources = []
    #     for config_file in files:
    #         logger.info("REST configuration file '%s'" % config_file)
    #         # Add all resources from this single JSON file
    #         resources.extend(self.single_rest(config_file))

    #     return resources
