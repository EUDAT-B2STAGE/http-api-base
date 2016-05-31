# -*- coding: utf-8 -*-

import logging

import os
import pkg_resources
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'
from logging.config import fileConfig
from confs.config import DEBUG, \
    LOGGING_CONFIG_FILE, REST_CONFIG_DIR, REST_CONFIG_INIT

myself = "Paolo D'Onorio De Meo <p.donoriodemeo@gmail.com>"
lic = "MIT"

AVOID_COLORS_ENV_LABEL = 'TESTING_FLASK'


################
# modify logging labels colors
if AVOID_COLORS_ENV_LABEL not in os.environ:
    logging.addLevelName(
        logging.CRITICAL,
        "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.CRITICAL))
    logging.addLevelName(
        logging.ERROR,
        "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(
        logging.WARNING,
        "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    logging.addLevelName(
        logging.INFO,
        "\033[1;32m%s\033[1;0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName(
        logging.DEBUG,
        "\033[1;35m%s\033[1;0m" % logging.getLevelName(logging.DEBUG))

################
# From the directory where the app is launched
PROJECT_DIR = '.'
CONFIG_DIR = 'confs'
LOG_CONFIG = os.path.join(PROJECT_DIR, CONFIG_DIR, LOGGING_CONFIG_FILE)
REST_CONFIG = os.path.join(PROJECT_DIR, CONFIG_DIR, REST_CONFIG_DIR)
REST_INIT = os.path.join(REST_CONFIG, REST_CONFIG_INIT)
DEFAULT_REST_CONFIG = 'example'

################
# LOGGING
if DEBUG:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
# Set default logging handler to avoid "No handler found" warnings.
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
# Read format and other things from file configuration
fileConfig(LOG_CONFIG)


def get_logger(name):
    """ Recover the right logger + set a proper specific level """
    if AVOID_COLORS_ENV_LABEL not in os.environ:
        name = "\033[1;90m%s\033[1;0m" % name
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    return logger


# # Does not work very well
# def silence_loggers(new_level=logging.ERROR):
#     """ Shut down log from other apps """

#     if '.' not in __package__:
#         name = __package__
#     else:
#         end = __package__.find('.')
#         name = __package__[:end]

#     from jinja2._compat import iteritems
#     for key, value in iteritems(logging.Logger.manager.loggerDict):
#         if isinstance(value, logging.Logger) and \
#          not key.startswith(name + '.') and \
#          not key.startswith(name):
#             print(key, value)
#             value.setLevel(new_level)

def silence_loggers():
    root_logger = logging.getLogger()
    first = True
    for handler in root_logger.handlers:
        if first:
            first = False
            continue
        root_logger.removeHandler(handler)
        #handler.close()
