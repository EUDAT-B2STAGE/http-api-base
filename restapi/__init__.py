# -*- coding: utf-8 -*-

# import os
import pkg_resources
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'
# from .confs.config import REST_CONFIG_DIR, BLUEPRINT_INIT

myself = "Paolo D'Onorio De Meo <p.donoriodemeo@gmail.com>"
lic = "MIT"

################
# From the directory where the app is launched
PROJECT_DIR = __package__

# ######################
# # TO FIX: remove this below when fixed swagger...
# CONFIG_DIR = 'confs'
# REST_CONFIG = os.path.join(PROJECT_DIR, CONFIG_DIR, REST_CONFIG_DIR)
# BLUEPRINT_FILE = os.path.join(REST_CONFIG, BLUEPRINT_INIT)
# DEFAULT_REST_CONFIG = 'example'
