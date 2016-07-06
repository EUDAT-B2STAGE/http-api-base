# -*- coding: utf-8 -*-

from __future__ import absolute_import
from .. import celery_app
from flask import current_app
from commons.logs import get_logger

logger = get_logger(__name__)


####################
# Define your celery tasks

@celery_app.task
def foo():
    with current_app.app_context():
        logger.debug("Test debug")
        logger.info("Test info")
