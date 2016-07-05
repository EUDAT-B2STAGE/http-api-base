# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the components here!
"""

from __future__ import absolute_import

import os
from flask import Flask, request, g  # , jsonify, got_request_exception
# from .jsonify import make_json_error
# from werkzeug.exceptions import default_exceptions
# from .jsonify import log_exception, RESTError
from commons.meta import Meta
from . import myself, lic
from commons.logs import get_logger

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


########################
# Configure Secret Key #
########################
def install_secret_key(app, filename='secret_key'):
    """

Found at
https://github.com/pallets/flask/wiki/Large-app-how-to

    Configure the SECRET_KEY from a file
    in the instance directory.

    If the file does not exist, print instructions
    to create it from a shell with a random key,
    then exit.
    """
    filename = os.path.join(app.instance_path, filename)

    try:
        app.config['SECRET_KEY'] = open(filename, 'rb').read()
    except IOError:
        logger.critical('No secret key!\n\nYou must create it with:')
        full_path = os.path.dirname(filename)
        if not os.path.isdir(full_path):
            print('mkdir -p {filename}'.format(filename=full_path))
        print('head -c 24 /dev/urandom > {filename}'.format(filename=filename))
        import sys
        sys.exit(1)


########################
# Flask App factory    #
########################
def create_app(name=__name__,
               enable_security=True, debug=False, testing=False, **kwargs):
    """ Create the server istance for Flask application """

    #################################################
    # Flask app instance
    #################################################
    from .confs import config
    microservice = Flask(name, **kwargs)

    if testing:
        microservice.config['TESTING'] = testing
    # else:
#         # Check and use a random file a secret key.
# # // TO FIX:
# # Maybe only in production?
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
        from .auth import auth
        auth.verify_token(custom_auth.verify_token)

        # Global namespace inside the Flask server
        @microservice.before_request
        def enable_global_authentication():
            # Save auth
            g._custom_auth = custom_auth
            # Save all databases/services
            g._services = internal_services

        # Enabling also OAUTH library
        from .oauth import oauth
        oauth.init_app(microservice)

        logger.info("FLASKING! Injected security internal module")

    ##############################
    # Restful plugin
    from .rest import Api, EndpointsFarmer, create_endpoints
    # Defining AUTOMATIC Resources
    current_endpoints = \
        create_endpoints(EndpointsFarmer(Api), enable_security, debug)
    # Restful init of the app
    current_endpoints.rest_api.init_app(microservice)

    ##############################
    # Init objects inside the app context
    with microservice.app_context():

        # Note:
        # Databases are already initialized inside the instances farm
        # Outside of the context
        # p.s. search inside this file for 'myclass('

        # Init users/roles for Security
        if enable_security:
            custom_auth.setup_secret(microservice.config['SECRET_KEY'])
            custom_auth.init_users_and_roles()

    ##############################
    # Logging responses
    @microservice.after_request
    def log_response(response):

        from commons.logs import obscure_passwords

        data = obscure_passwords(request.data)

        # Shrink too long data in log output
        for k in data:
            if not isinstance(data[k], str):
                continue
            if len(data[k]) > 255:
                data[k] = data[k][:255] + "..."

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
