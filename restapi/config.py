# -*- coding: utf-8 -*-

""" Configuration handler """

from __future__ import absolute_import
import os
from jinja2._compat import iteritems
from . import REST_CONFIG, BLUEPRINT_FILE
from commons.logs import get_logger
from commons.meta import Meta
try:
    import configparser
except:
    # python2
    import ConfigParser as configparser

from .jsonify import json

logger = get_logger(__name__)


class MyConfigs(object):
    """ A class to read all of my configurations """

    def read_config(self, configfile, case_sensitive=True):
        """ A generic reader for 'ini' files via standard library """

        sections = {}

        if case_sensitive:
            # Make sure configuration is case sensitive
            config = configparser.RawConfigParser()
            config.optionxform = str
        else:
            config = configparser.ConfigParser()

        # Read
        config.read(configfile)
        for section in config.sections():
            print(section)
            elements = {}
            for classname, endpoint in iteritems(dict(config.items(section))):
                print(classname, endpoint)
                elements[classname] = [endpoint]
            sections[str(section)] = elements

        return sections

    def read_complex_config(self, configfile):
        """ A more complex configuration is available in JSON format """
        content = {}
        with open(configfile) as fp:
            content = json.load(fp)
        return content

    def single_rest(self, config_file):

        meta = Meta()
        resources = []
        sections = {}

        if not os.path.exists(config_file):
            logger.warning("File '%s' does not exist! Skipping." % config_file)
            return resources

        #########################
        # Read the configuration inside this init file

        # JSON CASE
        try:
            sections = self.read_complex_config(config_file)
        except:  # json.commentjson.JSONLibraryException:
            logger.critical("Format error!\n" +
                            "'%s' file is not in JSON format" % config_file)
            exit(1)

        if 'apis' not in sections:
            logger.critical(
                "Section 'apis' not found in '%s' file" % config_file
            )
            exit(1)

        #########################
        # Use sections found
        for section, items in iteritems(sections['apis']):

            logger.debug("Configuration read: {Section: " + section + "}")

            module = meta.get_module_from_string(
                __package__ + '.resources.custom.' + section)
            # Skip what you cannot use
            if module is None:
                logger.warning("Could not find module '%s'..." % section)
                continue

            for classname, endpoints in iteritems(items):
                myclass = meta.get_class_from_string(classname, module)
                # Again skip
                if myclass is None:
                    continue
                else:
                    logger.debug("REST! Found resource: " +
                                 section + '.' + classname)

                # Get the best endpoint comparing inside against configuration
                instance = myclass()

                oldendpoint, endkey, endtype = instance.get_endpoint()
                if len(endpoints) < 1:
                    endpoints = [oldendpoint]

                endpoint_id = None
                if endkey is not None and endtype is not None:
                    endpoint_id = endtype + ':' + endkey

                resources.append((myclass, instance, endpoints, endpoint_id))

        return resources

    @staticmethod
    def load_and_handle_json_exception(file_handler):
        """
        Trying to avoid all the verbose error from commentjson
        """

        # Use also the original library
        import json as ojson

        error = None
        try:
            mydict = json.load(file_handler)
            return mydict
        except json.commentjson.JSONLibraryException as e:
            error = e
        except ojson.decoder.JSONDecodeError as e:
            error = e

        for line in str(error).split('\n')[::-1]:
            if line.strip() != '':
                error = line
                break
        logger.error("Failed to read JSON from '%s':\n%s"
                     % (file_handler.name, error))
        exit(1)

    def rest(self):
        """ REST endpoints from '.ini' files """

        logger.debug("Trying configurations from '%s' dir" % REST_CONFIG)

        files = []
        if os.path.exists(BLUEPRINT_FILE):
            with open(BLUEPRINT_FILE) as f:
                mydict = self.load_and_handle_json_exception(f)
                blueprint = mydict['blueprint']
                files.append(os.path.join(REST_CONFIG, blueprint + '.json'))
        else:
            logger.critical("Missing a blueprint file: %s" % BLUEPRINT_FILE)

        logger.debug("Resources files: '%s'" % files)

        resources = []
        for config_file in files:
            logger.info("REST configuration file '%s'" % config_file)
            # Add all resources from this single ini file
            resources.extend(self.single_rest(config_file))

        return resources
