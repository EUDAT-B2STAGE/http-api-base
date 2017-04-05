# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the internal flask  components here!
"""

import rapydo.confs as config
from flask import Flask as OriginalFlask, request
from flask_injector import FlaskInjector
from rapydo.protocols.cors import cors
from rapydo.rest.response import InternalResponse
from werkzeug.contrib.fixers import ProxyFix
from rapydo.rest.response import ResponseMaker
from rapydo.customization import Customizer
from rapydo.confs import PRODUCTION
from rapydo.utils.globals import mem
from rapydo.services.detect import authentication_service, \
    services as internal_services
from rapydo.protocols.restful import Api, EndpointsFarmer, create_endpoints
from rapydo.utils.logs import get_logger, \
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
            # log.very_verbose("Custom response built: %s" % out)
        except BaseException:
            log.debug("Response: [UNREADABLE OBJ]")
        responder = ResponseMaker(rv)

        # Avoid duplicating the response generation
        # or the make_response replica.
        # This happens with Flask exceptions
        if responder.already_converted():
            log.very_verbose("Response was already converted")
            # # Note: this response could be a class ResponseElements
            # return rv

            # The responder instead would have already found the right element
            return responder.get_original_response()

        # Note: jsonify gets done when calling the make_response,
        # so make sure that the data is written in  the right format!
        response = responder.generate_response()
        # print("DEBUG server.py", response)
        return super().make_response(response)


########################
# Flask App factory    #
########################
def create_app(name=__name__, worker_mode=False, testing_mode=False,
               enable_security=True, skip_endpoint_mapping=False, **kwargs):
    """ Create the server istance for Flask application """

    #############################
    # Initialize reading of all files
    mem.customizer = Customizer(testing_mode, PRODUCTION)
    # TO FIX: try to remove mem. from everywhere...

    #################################################
    # Flask app instance
    #################################################
    microservice = Flask(name, **kwargs)

    microservice.wsgi_app = ProxyFix(microservice.wsgi_app)

    ##############################
    # Add command line options

    # import click

    # @microservice.cli.command()
    # def init():
    #     """Initialize the current app"""
    #     click.echo('Init')

    ##############################
    # Cors
    cors.init_app(microservice)
    log.debug("FLASKING! Injected CORS")

    ##############################
    # Enabling our internal Flask customized response
    microservice.response_class = InternalResponse

    ##############################
    # Set app internal testing mode if create_app received the parameter
    if testing_mode:
        microservice.config['TESTING'] = testing_mode

    # Flask configuration from config file
    microservice.config.from_object(config)
    log.info("Flask app configured")

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

    ##############################
    # Disable security if launching celery workers
    if worker_mode:
        # TO FIX: it should pass we no problems in case?
        enable_security = False
        skip_endpoint_mapping = True

    ##############################
    # DATABASE/SERVICEs init and checks
    auth_backend_obj = None
    modules = []
    for injected, Injector in internal_services.items():

        args = {'app': microservice}
        if injected == 'authentication':
            args['extra_service'] = auth_backend_obj

        inj = Injector(**args)

        if injected == authentication_service:
            auth_backend_obj = inj

        log.debug("Append '%s' to plugged services" % injected)
        modules.append(inj)

    ##############################
    # Restful plugin
    if not skip_endpoint_mapping:
        # Triggering automatic mapping of REST endpoints
        current_endpoints = \
            create_endpoints(EndpointsFarmer(Api), enable_security)
        # Restful init of the app
        current_endpoints.rest_api.init_app(microservice)

        ##############################
        # Injection!
        # Enabling "configuration modules" for services to be injected
        # IMPORTANT: Injector must be initialized AFTER mapping endpoints
        FlaskInjector(app=microservice, modules=modules)

    ##############################
    # Clean app routes
    ignore_verbs = {"HEAD", "OPTIONS"}

    for rule in microservice.url_map.iter_rules():

        rulename = str(rule)
        # Skip rules that are only exposing schemas
        if '/schemas/' in rulename:
            continue

        endpoint = microservice.view_functions[rule.endpoint]
        if not hasattr(endpoint, 'view_class'):
            continue
        newmethods = ignore_verbs.copy()

        for verb in rule.methods - ignore_verbs:
            method = verb.lower()
            if method in mem.customizer._original_paths[rulename]:
                # remove from flask mapping
                # to allow 405 response
                newmethods.add(verb)
            else:
                log.verbose("Removed method %s.%s from mapping" %
                            (rulename, verb))

        rule.methods = newmethods

        # TO FIX: SOLVE CELERY INJECTION
        # # Set global objects for celery workers
        # if worker_mode:
        #     mem.services = internal_services

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
    # and the flask App is ready now:
    return microservice
