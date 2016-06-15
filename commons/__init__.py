# -*- coding: utf-8 -*-

import os
import pkg_resources
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'

myself = "Paolo D'Onorio De Meo <p.donoriodemeo@gmail.com>"
lic = "MIT"

PROJECT_DIR = __package__
CONFIG_DIR = 'confs'
LOGGING_CONFIG_FILE = 'logging_config.ini'
LOG_CONFIG = os.path.join(PROJECT_DIR, CONFIG_DIR, LOGGING_CONFIG_FILE)

AVOID_COLORS_ENV_LABEL = 'TESTING_FLASK'
