# -*- coding: utf-8 -*-

from __future__ import division, absolute_import
from . import myself, lic, get_logger

from flask_httpauth import HTTPTokenAuth

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

auth_type = 'Bearer'
auth = HTTPTokenAuth(auth_type)
logger.warning("Initizialized a valid authentication class: [%s]" % auth_type)
