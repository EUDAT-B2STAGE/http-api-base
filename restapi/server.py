# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import division, absolute_import

import os
from flask import Flask, request  # , jsonify, got_request_exception
# from .jsonify import make_json_error
# from werkzeug.exceptions import default_exceptions
# from .jsonify import log_exception, RESTError

from .resources.services.detect import GRAPHDB_AVAILABLE
from . import myself, lic, get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


###############################
def create_app(name=__name__, enable_security=True, debug=False, **kwargs):
    """ Create the server istance for Flask application """

    #################################################
    # Flask app instance
    #################################################
    from confs import config
    template_dir = os.path.join(config.BASE_DIR, __package__)
    microservice = Flask(name,
                         # Quick note:
                         # i use the template folder from the current dir
                         # just for Administration.
                         # I expect to have 'admin' dir here to change
                         # the default look of flask-admin
                         template_folder=template_dir,
                         **kwargs)

    # ##############################
    # # ERROR HANDLING
# This was commented as it eats up the real error
# even if it logs any error that happens,
# which is useful in production

    # # Handling exceptions with json
    # for code in default_exceptions.keys():
    #     microservice.error_handler_spec[None][code] = make_json_error
    # # Custom error handling: save to log
    # got_request_exception.connect(log_exception, microservice)

    # # Custom exceptions
    # @microservice.errorhandler(RESTError)
    # def handle_invalid_usage(error):
    #     response = jsonify(error.to_dict())
    #     response.status_code = error.status_code
    #     return response

    ##############################
    # Flask configuration from config file
    microservice.config.from_object(config)
    microservice.config['DEBUG'] = debug
# // TO FIX:
# development/production split?
    logger.info("FLASKING! Created application")

    #################################################
    # Other components
    #################################################

    ##############################
    # Cors
    from .cors import cors
    cors.init_app(microservice)
    logger.info("FLASKING! Injected CORS")

    # ##############################
    # # SQLALCHEMY INJECTION. Flask-Sqlalchemy DB
    # from .models import db
    # db.init_app(microservice)
    # logger.info("FLASKING! Injected sqlalchemy. (please use it)")

    ##############################
    # Flask security
    if enable_security:

        logger.info("FLASKING! Injecting security")

    """
    ## WORK IN PROGRESS!!

    # SHOULD LOAD MY AUTH CLASS
        # Dinamically load from a string chosen by the user the right module
        # or set a default by using containers environment variable
        # (need to set some priority too)
    """

    from .resources.services.authentication.graphdb import Authentication
    Authentication()

    ##############################
    # Restful plugin
    from .rest import epo, create_endpoints
    logger.info("FLASKING! Injected rest endpoints")
    epo = create_endpoints(epo, enable_security, debug)

    # Restful init of the app
    epo.rest_api.init_app(microservice)

    ##############################
    # Prepare database and tables
    with microservice.app_context():

        # INIT DATABASE?

        # SQLALCHEMY
        # try:
        #     if config.REMOVE_DATA_AT_INIT_TIME:
        #         db.drop_all()
        #     db.create_all()
        #     logger.info("DB: Connected and ready")
        # except Exception as e:
        #     logger.critical("Database connection failure: %s" % str(e))
        #     exit(1)

        # INIT USERS/ROLES FOR SECURITY
        if enable_security:

            logger.critical("SHOULD INIT USERS and ROLES HERE!")

            # if GRAPHDB_AVAILABLE:
            #     from .resources.services.accounting.graphbased \
            #         import init_graph_accounts
            #     init_graph_accounts()
            # else:
            #     # SQLALCHEMY
            #     from .security import db_auth
            #     # Prepare user/roles
            #     db_auth()

    # ##############################
    # # Flask admin
    # if enable_security and not GRAPHDB_AVAILABLE:
    #     from .admin import admin, UserView, RoleView
    #     from .models import User, Role
    #     from flask.ext.admin import helpers as admin_helpers

    #     admin.init_app(microservice)
    #     admin.add_view(UserView(User, db.session))
    #     admin.add_view(RoleView(Role, db.session))

    #     # Context processor for merging flask-admin's template context
    #     # into the flask-security views
    #     @security.context_processor
    #     def security_context_processor():
    #         return dict(admin_base_template=admin.base_template,
    #                     admin_view=admin.index_view, h=admin_helpers)

    #     logger.info("FLASKING! Injected admin endpoints")

    ##############################
    # Logging responses
    @microservice.after_request
    def log_response(response):
        logger.info("{} {} {} {}".format(
                    request.method, request.url, request.data, response))
        return response

    # OR
    # http://www.wiredmonk.me/error-handling-and-logging-in-flask-restful.html
    # WRITE TO FILE
    # file_handler = logging.FileHandler('app.log')
    # app.logger.addHandler(file_handler)
    # app.logger.setLevel(logging.INFO)

    ##############################
    # App is ready
    return microservice
