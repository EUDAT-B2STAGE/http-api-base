# -*- coding: utf-8 -*-

""" base in common for our flask internal extensions """

# TO FIX: create a base object for flask extensions like the injector

import abc
import time
from flask import _app_ctx_stack as stack
from injector import Module, singleton
from rapydo.confs import CUSTOM_PACKAGE
from rapydo.utils.meta import Meta
from rapydo.utils.logs import get_logger

log = get_logger(__name__)
meta = Meta()


class BaseExtension(metaclass=abc.ABCMeta):

    def __init__(self, app=None, variables={}, models={}):

        self.extra_service = None
        # a different name for each extended object
        self.name = self.__class__.__name__.lower()
        log.very_verbose("Opening service instance of %s" % self.name)

        self.app = app
        if app is not None:
            self.init_app(app)

        self.models = models
        self.variables = variables
        self.injected_name = variables.get('injected_name')
        log.very_verbose("Vars: %s" % variables)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

    # meta: get
    def get_object(self, ref=None):
        if ref is None:
            ref = self
        try:
            obj = getattr(ref, self.name)
        except AttributeError as e:
            # raise e
            log.critical_exit(
                "\nMissing extension connection.\n" +
                "Did you write a 'custom_connection' method inside " +
                self.name + " internal extension?\n" +
                "Did it return the connection object?\n" +
                "\nLogs:\n" + str(e)
            )
        return obj

    # meta: does it exist
    def has_object(self, ref=None):
        if ref is None:
            ref = self
        return hasattr(ref, self.name)

    # meta: set
    def set_object(self, obj, ref=None):
        if ref is None:
            ref = self
        setattr(ref, self.name, obj)

    def connect(self, **kwargs):

        obj = None

        # BEFORE
        self.pre_connection(**kwargs)

    #########################
    #########################
    # TO FIX: RETRY
        # Try until it's connected
        if len(kwargs) > 0:
            pass
        else:
            obj = self.retry()

        # # Last check
        # obj = self.get_object()
        # if obj is None:
        #     log.critical("Failed to connect: %s" % self.name)
        #     exit(1)
        # else:
        #     log.info("Connected! %s" % self.name)

    #########################
    #########################

        # AFTER
        self.post_connection(obj, **kwargs)

        # FINISH: we set models (empty by default)
        if obj is not None:
            obj = self.set_models_to_service(obj)

        return obj

    def set_models_to_service(self, obj):

        for name, model in self.models.items():
            # Save attribute inside class with the same name
            log.verbose("Injecting model '%s'" % name)
            setattr(obj, name, model)

        return obj

    def initialization(self, obj=None):
        """ Init operations require the app context """

        # # TODO: check in environment variables if to use context or not?
        # if self.variables.get('init_with_ctx', False):
        with self.app.app_context():
            self.custom_initialization(obj)

    def project_initialization(self):

        print("PROJECT INIT?")
        # TOFIX: allow a custom init method the project on any service?

        # # self.custom_project_initialization()

        # try:
        #     module_path = "%s.%s.%s" % (CUSTOM_PACKAGE, 'apis', 'services')
        #     custom_services = \
        #         meta.get_module_from_string(module_path, exit_on_fail=True)
        #     custom_services.init()
        # except BaseException:
        #     log.debug("No custom init available for mixed services")

        pass

    def set_connection_exception(self):
        return None

    def retry(self, retry_interval=3, max_retries=-1):
        retry_count = 0

        # Get the exception which will signal a missing connection
        exception = self.set_connection_exception()
        if exception is None:
            exception = BaseException

        while max_retries != 0 or retry_count < max_retries:

            retry_count += 1
            if retry_count > 1:
                log.verbose("testing again")

            try:
                obj = self.custom_connection()
            except exception as e:
                log.info("Service '%s' not available", self.name)
                log.debug("error is: %s" % e)
                time.sleep(retry_interval)
            # except BaseException as e:
            #     print("TEST EXCEPTION", e, type(e))
            #     time.sleep(retry_interval)
            else:
                break

        return obj

    def teardown(self, exception):
        ctx = stack.top
        if self.has_object(ref=ctx):
            self.close_connection(ctx)

    def get_instance(self, global_instance=True, **kwargs):

        obj = None
        ctx = stack.top
        unique_hash = str(sorted(kwargs.items()))
        log.very_verbose("instance hash: %s" % unique_hash)

        if ctx is None:
            # First connection, before any request
            self.initialization(obj=self.connect())

            # Once among the whole service, and as the last one:
            if self.name == 'authenticator':
                self.project_initialization()

            log.very_verbose("First connection for service %s" % self.name)

        else:
            if global_instance:
                # TODO: IMPORTANT! check if self is having only one instance
                # which makes it global
                reference = self
            else:
                reference = ctx

# TO FIX: use array for hash

            obj = self.get_object(ref=reference)
            if obj is None:
                obj = self.connect(**kwargs)
                self.set_object(obj=obj, ref=reference)

            log.verbose("Instance: %s(%s)" % (reference, obj))

        return obj

    ############################
    # OPTIONALLY
    # to be executed only at init time?

    def pre_connection(self, **kwargs):
        pass

    def post_connection(self, obj=None, **kwargs):
        pass

    def close_connection(self, ctx):
        """ override this method if you must close
        your connection after each request"""

        # obj = self.get_object(ref=ctx)
        # obj.close()
        self.set_object(obj=None, ref=ctx)  # to be overriden in case

    ############################
    # TO BE OVERRIDDEN
    @abc.abstractmethod
    def custom_initialization(self):
        pass

    @abc.abstractmethod
    def custom_connection(self):
        return


class BaseInjector(Module, metaclass=abc.ABCMeta):

    _models = {}
    _variables = {}
    singleton = singleton
    extension_instance = None
    injected_name = 'unknown'

    def __init__(self, app, extra_service=None):
        self.app = app
        self.extra_service = extra_service

    @classmethod
    def set_models(cls, base_models={}, custom_models={}):

        # Join models as described by issue #16
        cls._models = base_models
        for key, model in custom_models.items():

            # Verify if overriding
            if key in base_models.keys():
                original_model = base_models[key]
                # Override
                if issubclass(model, original_model):
                    log.very_verbose("Overriding model %s" % key)
                    cls._models[key] = model
                    continue

            # Otherwise just append
            cls._models[key] = model

        if len(cls._models) > 0:
            log.very_verbose("Loaded models")

    @classmethod
    def set_variables(cls, envvars):
        cls._variables = envvars

    # def internal_object(self):
    #     return self.extension_instance.get_instance()

    def configure(self, binder):

        # Get the Flask extension and its instance
        FlaskExtClass, flask_ext_obj = self.custom_configure()
        # Connect for the first time and initialize
        flask_ext_obj.get_instance()

    # TO FIX
        # # Passing the extra service for authentication
        # flask_ext_obj.extra_service = self.extra_service
        # # Binding between the class and the instance, for Flask requests
        # self.extension_instance = flask_ext_obj

        binder.bind(FlaskExtClass, to=flask_ext_obj, scope=self.singleton)
        return binder

    @abc.abstractmethod
    def custom_configure(self):
        return
