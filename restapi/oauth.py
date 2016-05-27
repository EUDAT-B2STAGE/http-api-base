# -*- coding: utf-8 -*-

"""
Oauth handling
"""

from __future__ import division, absolute_import
from . import get_logger
from flask_oauthlib.client import OAuth

logger = get_logger(__name__)

####################################
# Oauth2
oauth = OAuth()
logger.debug("Oauth2 object created")
