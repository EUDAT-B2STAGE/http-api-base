# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the internal flask  components here!
"""

from __future__ import absolute_import

import os
# from json.decoder import JSONDecodeError
from flask import Flask as OriginalFlask, request, g
from .response import ResponseMaker
from .resources.services.oauth2clients import ExternalServicesLogin as oauth2
from .confs.config import PRODUCTION, DEBUG as ENVVAR_DEBUG
from commons.meta import Meta
from commons.customization import Customizer
from commons.globals import mem
from commons.logs import get_logger, \
    handle_log_output, MAX_CHAR_LEN, set_global_log_level

#############################
# LOGS
log = get_logger(__name__)

# This is the first file to be imported in the project
# We need to enable many things on a global level for logs
set_global_log_level(package=__package__)


#############################
class Flask(OriginalFlask):

    def make_response(self, rv, response_log_max_len=MAX_CHAR_LEN):
        """
        Hack original flask response generator to read our internal response
        and build what is needed:
        the tuple (data, status, headers) to be eaten by make_response()
        """

        try:
            # Limit the output, sometimes it's too big
            out = str(rv)
            if len(out) > response_log_max_len:
                out = out[:response_log_max_len] + ' ...'

            log.very_verbose("MAKE_RESPONSE: %s" % out)
        except:
            log.debug("MAKE_RESPONSE: [UNREADABLE OBJ]")
        responder = ResponseMaker(rv)

        # Avoid duplicating the response generation
        # or the make_response replica.
        # This happens with Flask exceptions
        if responder.already_converted():
            log.verbose("Response was already converted")
            # # Note: this response could be a class ResponseElements
            # return rv

            # The responder instead would have already found the right element
            return responder.get_original_response()

        # Note: jsonify gets done when calling the make_response,
        # so make sure that the data is written in  the right format!
        response = responder.generate_response()
        # print("DEBUG server.py", response)
        return super().make_response(response)


def create_auth_instance(module, services, app, first_call=False):
    # This is the main object that drives authentication
    # inside our Flask server.
    # Note: to be stored inside the flask global context
    custom_auth = module.Authentication(services)

    # If oauth services are available, set them before every request
    if first_call or oauth2._check_if_services_exist():
        ext_auth = oauth2(app.config['TESTING'])
        custom_auth.set_oauth2_services(ext_auth._available_services)

    if not app.config['TESTING']:
        custom_auth.import_secret(app.config['SECRET_KEY_FILE'])

    return custom_auth


########################
# Flask App factory    #
########################
def create_app(name=__name__, debug=False,
               worker_mode=False, testing_mode=False,
               avoid_context=False, enable_security=True,
               skip_endpoint_mapping=False,
               **kwargs):
    """ Create the server istance for Flask application """

    #############################
    # Initialize reading of all files
    # TO FIX: remove me
    mem.customizer = Customizer(__package__)

    #################################################
    # Flask app instance
    #################################################
    from .confs import config
    microservice = Flask(name, **kwargs)

    ##############################
    # @microservice.before_first_request
    # def first():
    #     print("BEFORE THE VERY FIRST REQUEST", g)

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
    ##############################
    # Flask configuration from config file
    microservice.config.from_object(config)

    if ENVVAR_DEBUG is not None:
        try:
            tmp = int(ENVVAR_DEBUG) == 1
        except:
            tmp = str(ENVVAR_DEBUG).lower() == 'true'
        debug = tmp  # bool(tmp)
    microservice.config['DEBUG'] = debug
    log.info("Flask application generated")

    ##############################
    if PRODUCTION:

        log.info("Production server mode is ON")

        # TO FIX: random secrety key in production
        # # Check and use a random file a secret key.
        # install_secret_key(microservice)

        # # To enable exceptions printing inside uWSGI
        # # http://stackoverflow.com/a/17839750/2114395
        # from werkzeug.debug import DebuggedApplication
        # app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

    #################################################
    # Other components
    #################################################

    ##############################
    # Cors
    from .cors import cors
    cors.init_app(microservice)
    log.debug("FLASKING! Injected CORS")

    ##############################
    # DATABASE/SERVICEs CHECKS
    from .resources.services.detect import services as internal_services
    for service, myclass in internal_services.items():
        log.debug("Available service %s" % service)
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
        log.debug("Trying to load the module %s" % module_name)
        module = meta.get_module_from_string(module_name)

        # At init time, verify and build Oauth services if any
        init_auth = create_auth_instance(
            module, internal_services, microservice, first_call=True)

        # Enabling also OAUTH library
        from .oauth import oauth
        oauth.init_app(microservice)

        @microservice.before_request
        def enable_authentication_per_request():
            """ Save auth object """

            # Authentication the right (per-instance) way
            custom_auth = create_auth_instance(
                module, internal_services, microservice)

            # Save globally across the code
            g._custom_auth = custom_auth

        log.info("FLASKING! Injected security internal module")

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
        # Triggering automatic mapping of REST endpoints
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
                mem.services = internal_services

            # Note:
            # Databases are already initialized inside the instances farm
            # Outside of the context
            # p.s. search inside this file for 'myclass('

            # Init users/roles for Security
            if enable_security:
                init_auth.init_users_and_roles()

            # Allow a custom method for mixed services init
            try:
                from .resources.custom import services as custom_services
                custom_services.init(internal_services, enable_security)
            except:
                log.debug("No custom init available for mixed services")

    ##############################
    # Logging responses
    @microservice.after_request
    def log_response(response):

        data = handle_log_output(request.data)

        # Limit the parameters string size, sometimes it's too big
        for k in data:
            # print("K", k, "DATA", data)
            try:
                if not isinstance(data[k], str):
                    continue
                if len(data[k]) > MAX_CHAR_LEN:
                    data[k] = data[k][:MAX_CHAR_LEN] + "..."
            except IndexError:
                pass

        log.info("{} {} {} {}".format(
                 request.method, request.url, data, response))
        return response

    ##############################
    # Enabling user callbacks after a request
    @microservice.after_request
    def call_after_request_callbacks(response):
        for callback in getattr(g, 'after_request_callbacks', ()):
            callback(response)
        return response

    # ##############################
    # log.critical("test")
    # log.error("test")
    # log.warning("test")
    # log.info("test")
    # log.debug("test")
    # log.verbose("test")
    # log.very_verbose("test")
    # log.pp(microservice)
    # log.critical_exit("test")

    ##############################
    # App is ready
    return microservice
