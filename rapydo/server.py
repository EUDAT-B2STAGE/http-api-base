# -*- coding: utf-8 -*-

"""
Main server factory.
We create all the internal flask  components here!
"""

from flask import Flask as OriginalFlask, request, g
from werkzeug.contrib.fixers import ProxyFix
from rapydo.rest.response import ResponseMaker
from rapydo.customization import Customizer
from rapydo.confs import PRODUCTION, DEBUG as ENVVAR_DEBUG
from rapydo.utils.globals import mem
from rapydo.services.detect import \
    services as internal_services, \
    services_classes as injectable_services

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

            log.verbose("Custom response built: %s" % out)
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
def create_app(name=__name__, debug=False,
               worker_mode=False, testing_mode=False,
               avoid_context=False, enable_security=True,
               skip_endpoint_mapping=False,
               **kwargs):
    """ Create the server istance for Flask application """

# TO FIX: REMOVE ME
    debug = True
# REMOVE ME

    #############################
    # Initialize reading of all files
    # TO FIX: remove me
    mem.customizer = Customizer(testing_mode, PRODUCTION)

    #################################################
    # Flask app instance
    #################################################
    # from rapydo.confs import config
    import rapydo.confs as config
    microservice = Flask(name, **kwargs)
    microservice.wsgi_app = ProxyFix(microservice.wsgi_app)

    ##############################
    # Disable security if launching celery workers
    if worker_mode:
        enable_security = False
        skip_endpoint_mapping = True

    # Set app internal testing mode if create_app received the parameter
    if testing_mode:
        microservice.config['TESTING'] = testing_mode
    ##############################
    # Flask configuration from config file
    microservice.config.from_object(config)

    if ENVVAR_DEBUG is not None:
        try:
            tmp = int(ENVVAR_DEBUG) == 1
        except BaseException:
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
    # DATABASE/SERVICEs init and checks
    modules = []
    for name, ConfigureInjection in internal_services.items():
        modules.append(ConfigureInjection(microservice))

    ##############################
    # Cors
    from rapydo.protocols.cors import cors
    cors.init_app(microservice)
    log.debug("FLASKING! Injected CORS")

    ##############################
    # Enabling our internal Flask customized response
    from rapydo.rest.response import InternalResponse
    microservice.response_class = InternalResponse

###################################
# QUICK PROTOTYPE
###################################

    # from injector import inject
    # from flask_restful import Api, Resource
    # api = Api(microservice)

    # from rapydo.protocols.bearer import authentication

    # class HelloWorld(Resource):

    #     @inject(**injectable_services)
    #     def __init__(self, **injected_services):

    #         ################
    #         # AUTH
    #         self.auth = injected_services.pop('authentication').connection
    #         # set here "services" for auth
    #         self.auth.set_services(injected_services)
    #         print("YEAH", self.auth._db)
    #         return
    #         ################

    #         self.auth = injected_services.pop('authentication')
    #         # print("Services:", injected_services)
    #         self.irods = injected_services.get('irods')
    #         self.neo4j = injected_services.get('neo4j')
    #         self.sql = injected_services.get('sqlalchemy')

    #     def send_errors(self, **kwargs):
    #         print("ERROR", kwargs)
    #         return kwargs.get('message')

    #     @authentication.authorization_required
    #     def get(self):

    #         return {'hello': 'world'}

    #         ####################
    #         print("authentication:", self.auth.connection)

    #         ####################
    #         print("neomodel connection:", self.neo4j.connection)
    #         test = self.neo4j.Role(name="pippo").save()
    #         print("neomodel test:", test)

    #         ####################
    #         print("irods connection:", self.irods.connection)
    #         coll = self.irods.connection.collections.get('/tempZone')
    #         print("root object:", coll)
    #         for col in coll.subcollections:
    #             print("collection:", col)

    #         ####################
    #         print("alchemy connection:", self.sql.connection)
    #         res = None
    #         res = self.sql.User.query.all()
    #         print("tmp", res)

    #         ####################
    #         return {'hello': 'world'}

    # api.add_resource(HelloWorld, '/foo')

    ##############################
    # Enabling configuration modules for services to be injected
    from flask_injector import FlaskInjector
    FlaskInjector(app=microservice, modules=modules)

    # return microservice
###################################
###################################

# UHM ? WHY ?
    # if not worker_mode:
    #     # Global namespace inside the Flask server
    #     @microservice.before_request
    #     def enable_global_services():
    #         """ Save all databases/services """
    #         g._services = internal_services

    ##############################
    # Restful plugin
    if not skip_endpoint_mapping:
        from rapydo.protocols.restful import \
            Api, EndpointsFarmer, create_endpoints
        # Triggering automatic mapping of REST endpoints
        current_endpoints = \
            create_endpoints(EndpointsFarmer(Api), enable_security, debug)
        # Restful init of the app
        current_endpoints.rest_api.init_app(microservice)

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


# UHM?

    # ##############################
    # # Init objects inside the app context
    # if not avoid_context:
    #     with microservice.app_context():

    #         # Set global objects for celery workers
    #         if worker_mode:
    #             mem.services = internal_services

    #         # Note:
    #         # Databases are already initialized inside the instances farm
    #         # Outside of the context
    #         # p.s. search inside this file for 'myclass('

    #         # Init users/roles for Security
    #         if enable_security:
    #             init_auth.init_users_and_roles()

    #         ####################
    #             # TODO: check this piece of code
    #             if PRODUCTION and init_auth.check_if_user_defaults():
    #                 raise AttributeError(
    #                     "Starting production mode with default admin user")
    #         ####################

    #         # Allow a custom method for mixed services init
    #         try:
    #             from custom import services as custom_services
    #             custom_services.init(internal_services, enable_security)
    #         except BaseException:
    #             log.debug("No custom init available for mixed services")

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
