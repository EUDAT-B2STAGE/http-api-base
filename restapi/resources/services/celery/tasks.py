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

# from __future__ import absolute_import

from commons.services import ServiceFarm, ServiceObject
from commons.services.celery import celery_app
from commons.logs import get_logger

logger = get_logger(__name__)


class MyCelery(ServiceObject):

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
        # Or is celery going to give us error if that does not work?

        # self._flask_app = app
        celery = self.get_instance(app)
        logger.debug("Celery queue is available")
        return celery

    def get_instance(self, app=None):
        if self._celery_app is None:
            self._celery_app = MyCelery(app)._current
        return self._celery_app
