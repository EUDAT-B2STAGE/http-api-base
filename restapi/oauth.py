# -*- coding: utf-8 -*-

"""
Oauth handling
"""

# from __future__ import absolute_import
from flask_oauthlib.client import OAuth
from restapi.utils.logs import get_logger

log = get_logger(__name__)

####################################
# Oauth2
oauth = OAuth()
log.debug("Oauth2 object created")
