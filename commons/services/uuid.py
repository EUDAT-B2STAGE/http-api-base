# -*- coding: utf-8 -*-

"""
Handling IDs in a more secure way
"""

from __future__ import absolute_import
import uuid
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def getUUID():
    return str(uuid.uuid4())
