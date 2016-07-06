# -*- coding: utf-8 -*-

from __future__ import absolute_import
from ...services.celery import celery_app
from flask import current_app
from commons.logs import get_logger

logger = get_logger(__name__)


####################
# Define your celery tasks

@celery_app.task
def foo():
    logger.debug("Test debug")
    logger.info("Test info")


@celery_app.task
def foo_in_context(arg):
    with current_app.app_context():
        logger.debug("Test debug '%s'" % arg)
        logger.info("Test info '%s'" % arg)
