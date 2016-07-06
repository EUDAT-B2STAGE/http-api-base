# -*- coding: utf-8 -*-

"""
Celery pattern. Some interesting read here:

http://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern

Of course that discussion is not enough for
a flask templating framework like ours.
So we made some improvement along the code.

"""

from commons.services.celery import celery_app

## Try
    # commons.tasks.custom
## Except
    # commons.tasks.base

from restapi.server import create_app
from commons.meta import Meta
from commons.logs import get_logger

logger = get_logger(__name__)
meta = Meta()

main_package = "commons.tasks."

# Base tasks
submodules = meta.import_submodules_from_package(main_package + "base")
# Custom tasks
submodules = meta.import_submodules_from_package(main_package + "custom")

# Reload Flask app code also for the worker
# This is necessary to have the app context available
app = create_app(enable_security=False, avoid_context=True, debug=True)
app.app_context().push()

# celery_app = MyCelery(app)._current
logger.debug("Celery %s" % celery_app)
