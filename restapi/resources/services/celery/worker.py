# -*- coding: utf-8 -*-

"""
Celery pattern. Some interesting read here:

http://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern

Of course that discussion is not enough for
a flask templating framework like ours.
So we made some improvement along the code.

"""

# from restapi.resources.services.celery.tasks import MyCelery
from commons.services.celery import celery_app
# TO FIX: can we import from __package__ instead?
from restapi.server import create_app
from commons.meta import Meta
from commons.logs import get_logger

log = get_logger(__name__)

################################################
# Reload Flask app code also for the worker
# This is necessary to have the app context available
app = create_app(worker_mode=True, debug=True)

# Recover celery app with current app
# celery_app = MyCelery(app)._current

# celery_app = MyCelery(app)._current
log.debug("Celery %s" % celery_app)

################################################
# Import tasks modules to make sure all tasks are avaiable

meta = Meta()
main_package = "commons.tasks."
# Base tasks
submodules = meta.import_submodules_from_package(main_package + "base")
# Custom tasks
submodules = meta.import_submodules_from_package(main_package + "custom")
