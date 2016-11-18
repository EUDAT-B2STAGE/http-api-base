# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the internal flask  components here!
"""

from __future__ import absolute_import

import os
from json.decoder import JSONDecodeError
from flask import Flask as OriginalFlask, request, g
from .response import ResponseMaker
from commons.meta import Meta
from commons.logs import get_logger

from . import myself, lic

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class Flask(OriginalFlask):

    def make_response(self, rv):
        """
        Hack original flask response generator to read our internal response
        and build what is needed:
        the tuple (data, status, headers) to be eaten by make_response()
        """

## TO FIX:
# use some global variable to enable/disable the usual response
        # # In case you want to get back to normal
        # return super().make_response(rv)

        try:
            logger.info("MAKE_RESPONSE: %s" % rv)
        except:
            logger.info("MAKE_RESPONSE: [UNREADABLE OBJ]")
        responder = ResponseMaker(rv)

        # Avoid duplicating the response generation
        # or the make_response replica.
        # This happens with Flask exceptions
        if responder.already_converted():
            logger.debug("Response was already converted")
            # # Note: this response could be a class ResponseElements
            # return rv

            # The responder instead would have already found the right element
            return responder.get_original_response()

        # Note: jsonify gets done when calling the make_response,
        # so make sure that the data is of the right format!
        return super().make_response(responder.generate_response())


# ########################
# # Configure Secret Key #
# ########################
# def install_secret_key(app, filename='secret_key'):
#     """

# Found at
# https://github.com/pallets/flask/wiki/Large-app-how-to

#     Configure the SECRET_KEY from a file
#     in the instance directory.

#     If the file does not exist, print instructions
#     to create it from a shell with a random key,
#     then exit.
#     """
#     filename = os.path.join(app.instance_path, filename)

#     try:
#         app.config['SECRET_KEY'] = open(filename, 'rb').read()
#     except IOError:
#         logger.critical('No secret key!\n\nYou must create it with:')
#         full_path = os.path.dirname(filename)
#         if not os.path.isdir(full_path):
#             print('mkdir -p {filename}'.format(filename=full_path))
#         print('head -c 24 /dev/urandom > {filename}'.format(filename=filename))
#         import sys
#         sys.exit(1)


########################
# Flask App factory    #
########################
def create_app(name=__name__, debug=False,
               worker_mode=False, testing_mode=False,
               avoid_context=False, enable_security=True,
               skip_endpoint_mapping=False,
               **kwargs):
    """ Create the server istance for Flask application """

    #################################################
    # Flask app instance
    #################################################
    from .confs import config
    microservice = Flask(name, **kwargs)

    ##############################
    # @microservice.before_request
    # def before():
    #     print("BEFORE EVERY REQUEST...")

    # @microservice.after_request
    # def after(response):
    #     print("AFTER EVERY REQUEST...")
    #     return response

    ##############################
    # Disable security if launching celery workers
    if worker_mode:
        enable_security = False

    # Set app internal testing mode if create_app received the parameter
    if testing_mode:
        microservice.config['TESTING'] = testing_mode
    else:
# # // TO FIX:
# # Maybe only in production?
        pass
#         # Check and use a random file a secret key.
#         install_secret_key(microservice)

    ##############################
    # Flask configuration from config file
    microservice.config.from_object(config)
    microservice.config['DEBUG'] = debug
    # Set the new level of debugging
    logger = get_logger(__name__, debug)
    logger.info("FLASKING! Created application")

    #################################################
    # Other components
    #################################################

    ##############################
    # Cors
    from .cors import cors
    cors.init_app(microservice)
    logger.info("FLASKING! Injected CORS")

    ##############################
    # DATABASE/SERVICEs CHECKS
    from .resources.services.detect import services as internal_services
    for service, myclass in internal_services.items():
        logger.info("Available service %s" % service)
        myclass(check_connection=True, app=microservice)

    ##############################
    # Enabling our internal Flask customized response
    from .response import InternalResponse
    microservice.response_class = InternalResponse

    ##############################
    # Flask security
    if enable_security:

        # Dynamically load the authentication service
        meta = Meta()
        module_base = __package__ + ".resources.services.authentication"
        auth_service = os.environ.get('BACKEND_AUTH_SERVICE', '')
        module_name = module_base + '.' + auth_service
        logger.debug("Trying to load the module %s" % module_name)
        module = meta.get_module_from_string(module_name)

        # This is the main object that drives authentication
        # inside our Flask server.
        # Note: to be stored inside the flask global context
        custom_auth = module.Authentication(internal_services)

        # Verify if we can inject oauth2 services into this module
        from .resources.services.oauth2clients import ExternalServicesLogin
        oauth2 = ExternalServicesLogin(microservice.config['TESTING'])
        custom_auth.set_oauth2_services(oauth2._available_services)

        # Instead of using the decorator
        # Applying Flask_httpauth lib to the current instance
        from .auth import authentication
        authentication.callbacks(
            verify_token_f=custom_auth.verify_token,
            verify_roles_f=custom_auth.verify_roles)

        # Global namespace inside the Flask server
        @microservice.before_request
        def enable_global_authentication():
            """ Save auth object """
            g._custom_auth = custom_auth

        # Enabling also OAUTH library
        from .oauth import oauth
        oauth.init_app(microservice)

        logger.info("FLASKING! Injected security internal module")

    if not worker_mode:
        # Global namespace inside the Flask server
        @microservice.before_request
        def enable_global_services():
            """ Save all databases/services """
            g._services = internal_services

    ##############################
    # Restful plugin
    if not skip_endpoint_mapping:
        from .rest import Api, EndpointsFarmer, create_endpoints
        # Defining AUTOMATIC Resources
        current_endpoints = \
            create_endpoints(EndpointsFarmer(Api), enable_security, debug)
        # Restful init of the app
        current_endpoints.rest_api.init_app(microservice)

    ##############################
    # Init objects inside the app context
    if not avoid_context:
        with microservice.app_context():

            # Set global objects for celery workers
            if worker_mode:
                from commons.globals import mem
                mem.services = internal_services

            # Note:
            # Databases are already initialized inside the instances farm
            # Outside of the context
            # p.s. search inside this file for 'myclass('

            # Init users/roles for Security
            if enable_security:
                custom_auth.setup_secret(microservice.config['SECRET_KEY'])
                custom_auth.init_users_and_roles()

            # Allow a custom method for mixed services init
            try:
                from .resources.custom import services as custom_services
                custom_services.init(internal_services, enable_security)
            except:
                logger.debug("No custom init available for mixed services")

    ##############################
    # Logging responses
    @microservice.after_request
    def log_response(response):

        from commons.logs import obscure_passwords

        try:
            data = obscure_passwords(request.data)
        except JSONDecodeError:
            data = request.data

        # Shrink too long data in log output
        for k in data:
            # print("K", k, "DATA", data)
            try:
                if not isinstance(data[k], str):
                    continue
                if len(data[k]) > 255:
                    data[k] = data[k][:255] + "..."
            except IndexError:
                pass

        logger.info("{} {} {} {}".format(
                    request.method, request.url,
                    data, response))
        return response

    ##############################
    # Enabling user callbacks after a request
    @microservice.after_request
    def call_after_request_callbacks(response):
        for callback in getattr(g, 'after_request_callbacks', ()):
            callback(response)
        return response

    ##############################
    # App is ready
    return microservice
