# -*- coding: utf-8 -*-

"""

Tasks queued for asynchronous operations.

This service is quite anonymous.
I use the Celery class and farm just to make sure
that we tie the celery application to Flask,
and to check the connection at initialization time.

How to add a task:

@celery_app.task
def my_async_task(arg):
    logger.debug("This is asynchronous: %s" % arg)

"""

from __future__ import absolute_import

import os
from celery import Celery
from commons.logs import get_logger
from commons.services import ServiceFarm

logger = get_logger(__name__)

REDIS_HOST = os.environ.get('QUEUE_NAME').split('/')[::-1][0]
REDIS_PORT = int(os.environ.get('QUEUE_PORT').split(':')[::-1][0])
REDIS_BROKER_URL = 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT)

celery_app = Celery(
    'RestApiQueue',
    backend=REDIS_BROKER_URL,
    # backend=app.config['CELERY_BACKEND'],
    broker=REDIS_BROKER_URL,
    # broker=app.config['CELERY_BROKER_URL']
)

# Skip initial warnings, avoiding pickle
celery_app.conf.CELERY_ACCEPT_CONTENT = ['json']
celery_app.conf.CELERY_TASK_SERIALIZER = 'json'
celery_app.conf.CELERY_RESULT_SERIALIZER = 'json'


class MyCelery(object):

    def __init__(self, app):
        self._current = self.make_celery(app)

    def make_celery(self, app):
        """
        Following the snippet on:
        http://flask.pocoo.org/docs/0.11/patterns/celery/
        """

        celery_app.conf.update(app.config)
        TaskBase = celery_app.Task

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

        celery_app.Task = ContextTask
        return celery_app


class CeleryFarm(ServiceFarm):

    _celery_app = None

    @staticmethod
    def define_service_name():
        return 'celery'

    def init_connection(self, app):

# // TO FIX:
        # Should we check also the REDIS connection?
        # Or celery is going to give us error if that does not work?

        # self._flask_app = app
        celery = self.get_instance(app)
        logger.debug("Celery queue is available")
        return celery

    def get_instance(self, app=None):
        if self._celery_app is None:
            self._celery_app = MyCelery(app)._current
        return self._celery_app
