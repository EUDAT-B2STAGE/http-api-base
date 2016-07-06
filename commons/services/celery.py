# -*- coding: utf-8 -*-

"""
Celery tasks
"""

import os
from celery import Celery

REDIS_HOST = os.environ.get('QUEUE_NAME').split('/')[::-1][0]
REDIS_PORT = int(os.environ.get('QUEUE_PORT').split(':')[::-1][0])
REDIS_BROKER_URL = 'redis://%s:%s/0' % (REDIS_HOST, REDIS_PORT)

celery_app = Celery(
    'RestApiQueue',
    backend=REDIS_BROKER_URL,
    broker=REDIS_BROKER_URL,
)

# Skip initial warnings, avoiding pickle format (deprecated)
celery_app.conf.CELERY_ACCEPT_CONTENT = ['json']
celery_app.conf.CELERY_TASK_SERIALIZER = 'json'
celery_app.conf.CELERY_RESULT_SERIALIZER = 'json'
