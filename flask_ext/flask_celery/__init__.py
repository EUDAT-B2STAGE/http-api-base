# -*- coding: utf-8 -*-

"""
Celery extension wrapper

"""
import os
from flask_ext import BaseInjector, BaseExtension, get_logger
from celery import Celery

log = get_logger(__name__)


class CeleryExt(BaseExtension):

    def custom_connection(self):

        broker = self.variables.get("broker")

        if broker is None:
            broker = "UNKNOWN"

        HOST = self.variables.get("broker_host")
        PORT = int(self.variables.get("broker_port"))
        if broker == 'RABBIT':

            # BROKER_URL = 'amqp://guest:guest@%s:%s/0' % (HOST, PORT)
            BROKER_URL = 'amqp://%s:%s' % (HOST, PORT)
            BROKER_URL = 'amqp://%s' % (HOST)
            BACKEND_URL = 'rpc://%s:%s/0' % (HOST, PORT)
            log.info("Found RabbitMQ as Celery broker %s" % BROKER_URL)
        elif broker == 'REDIS':
            BROKER_URL = 'redis://%s:%s/0' % (HOST, PORT)
            BACKEND_URL = 'redis://%s:%s/0' % (HOST, PORT)
            log.info("Found Redis as Celery broker %s" % BROKER_URL)
        else:
            log.error("Unable to start Celery, missing broker service")
            self.celery_app = None
            return self.celery_app

        self.celery_app = Celery(
            'RestApiQueue',
            backend=BACKEND_URL,
            broker=BROKER_URL,
        )

        from celery.task.control import inspect
        insp = inspect()
        if not insp.stats():
            log.warning("No running Celery workers were found")

        # Skip initial warnings, avoiding pickle format (deprecated)
        self.celery_app.conf.CELERY_ACCEPT_CONTENT = ['json']
        self.celery_app.conf.CELERY_TASK_SERIALIZER = 'json'
        self.celery_app.conf.CELERY_RESULT_SERIALIZER = 'json'

        return self.celery_app

    def custom_initialization(self):
        pass


class CeleryInjector(BaseInjector):

    def custom_configure(self):
        celery = CeleryExt(self.app, self._variables)
        return CeleryExt, celery
