# -*- coding: utf-8 -*-

"""

Move here the logic for any logs

"""

from __future__ import absolute_import
import os
import json
import logging
from logging.config import fileConfig
from . import AVOID_COLORS_ENV_LABEL, LOG_CONFIG

OBSCURED_FIELDS = ['password', 'pwd', 'token']


################
# LOGGING

class LogMe(object):

    """ A common logger to be used all around development packages """

    _log_level = logging.INFO
    _colors_enabled = True

    def __init__(self, debug=True):

        super(LogMe, self).__init__()
        self.set_debug(debug)

        if AVOID_COLORS_ENV_LABEL in os.environ:
            self._colors_enabled = False

        # Set default logging handler to avoid "No handler found" warnings.
        try:  # Python 2.7+
            from logging import NullHandler
        except ImportError:
            class NullHandler(logging.Handler):
                def emit(self, record):
                    pass

        # Make sure there is at least one logger
        logging.getLogger(__name__).addHandler(NullHandler())
        # Format
        fileConfig(LOG_CONFIG)

        ################
        # modify logging labels colors
        if self._colors_enabled:
            logging.addLevelName(
                logging.CRITICAL, "\033[1;41m%s\033[1;0m"
                % logging.getLevelName(logging.CRITICAL))
            logging.addLevelName(
                logging.ERROR, "\033[1;31m%s\033[1;0m"
                % logging.getLevelName(logging.ERROR))
            logging.addLevelName(
                logging.WARNING, "\033[1;33m%s\033[1;0m"
                % logging.getLevelName(logging.WARNING))
            logging.addLevelName(
                logging.INFO, "\033[1;32m%s\033[1;0m"
                % logging.getLevelName(logging.INFO))
            logging.addLevelName(
                logging.DEBUG, "\033[1;35m%s\033[1;0m"
                % logging.getLevelName(logging.DEBUG))

    def set_debug(self, debug):
        self.debug = debug
        if self.debug:
            self._log_level = logging.DEBUG
        else:
            self._log_level = logging.INFO

    def get_new_logger(self, name):
        """ Recover the right logger + set a proper specific level """
        if self._colors_enabled:
            name = "\033[1;90m%s\033[1;0m" % name
        logger = logging.getLogger(name)
        logger.setLevel(self._log_level)
        return logger

please_logme = LogMe()


def get_logger(name, debug_setter=None):
    """ Recover the right logger + set a proper specific level """
    if debug_setter is not None:
        please_logme.set_debug(debug_setter)

    return please_logme.get_new_logger(name)


def silence_loggers():
    root_logger = logging.getLogger()
    first = True
    for handler in root_logger.handlers:
        if first:
            first = False
            continue
        root_logger.removeHandler(handler)
        # handler.close()


def obscure_passwords(original_parameters_string):

    """ Avoid printing passwords! """
    if (original_parameters_string is None):
        return {}

    mystr = original_parameters_string.decode("ascii")
    if mystr.strip() == '':
        return {}

    parameters = json.loads(mystr)
    for key, value in parameters.items():
        if key in OBSCURED_FIELDS:
            value = '****'
        parameters[key] = value
    return parameters


def pretty_print(myobject, prefix_line=None):
    """
    Make object(s) and structure(s) clearer to debug
    """

    if prefix_line is not None:
        print("PRETTY PRINT [%s]" % prefix_line)
    from beeprint import pp
    pp(myobject)
    return
