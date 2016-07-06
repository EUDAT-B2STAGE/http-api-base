# -*- coding: utf-8 -*-

"""
Celery pattern

http://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern
"""

from restapi.resources.services.celery.tasks import MyCelery

# Reload Flask app code also for the worker
from restapi.server import create_app
app = create_app(enable_security=False, avoid_context=True, debug=True)
# app.app_context().push()

celery_app = MyCelery(app)._current
