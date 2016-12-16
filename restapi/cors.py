# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import division, absolute_import
from . import myself, lic
from commons.logs import get_logger
from flask_cors import CORS

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


# ####################################
# Allow cross-domain requests
# e.g. for JS and Upload

cors = CORS(
    # allow_headers=['Content-Type'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
logger.debug("Flask: creating CORS")

# # WARNING: in case 'cors' write too much, you could fix it like this
# import logging
# corslogger = logging.getLogger('.server.cors')
# corslogger.setLevel(logging.WARNING)
