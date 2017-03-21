# -*- coding: utf-8 -*-

""" base in common for our flask internal extensions """

# TO FIX: create a base object for flask extensions like the injector

import abc
import time
import logging
from flask import _app_ctx_stack as stack
from injector import Module, singleton


####################
# TO FIX: # how to use logs inside this extensions?
# should we make a Flask extension or a Python package out of logging?
def get_logger(name, level=logging.VERY_VERBOSE):
    import logging
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
####################


log = get_logger(__name__)


class BaseExtension(metaclass=abc.ABCMeta):

    def __init__(self, app=None, variables={}, models={}):

        self.injected_name = None
        self.extra_service = None
        # a different name for each extended object
        self.name = self.__class__.__name__.lower()
        log.very_verbose("Opening service instance of %s" % self.name)

        self.app = app
        if app is not None:
            self.init_app(app)

        self.models = models
        self.variables = variables
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
            log.error(
                "\nMissing extension connection.\n" +
                "Did you write a 'custom_connection' method inside " +
                self.name + " internal extension?\n" +
                "Did it return the connection object?\n" +
                "\nLogs:\n" + str(e)
            )
            exit(1)
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

    def connect(self):
        # Try until it's connected
        self.retry()

        # Last check
        obj = self.get_object()
        if obj is None:
            log.critical("Failed to connect: %s" % self.name)
            exit(1)
        else:
            log.info("Connected! %s" % self.name)

        self.post_connection(obj)
        return self.set_models_to_service(obj)

    def set_models_to_service(self, obj):

        for name, model in self.models.items():
            # Save attribute inside class with the same name
            log.verbose("Injecting model '%s'" % name)
            setattr(obj, name, model)

        return obj

    def initialization(self):
        """ Init operations require the app context """
        with self.app.app_context():
            self.custom_initialization()

    def project_initialization(self):

        # Allow a custom method for mixed services init
        try:
            # TO FIX: to be redefined
            from custom import services as custom_services
            custom_services.init()
        except BaseException:
            log.debug("No custom init available for mixed services")

    # TODO: allow a custom init method the project on any service?
        pass

    def test_connection(self):
        try:
            self.set_object(obj=self.custom_connection())
            return True
        # except Exception as e:
        #     raise e
        except BaseException:
            return False

    def retry(self, retry_interval=5, max_retries=-1):
        retry_count = 0
        while max_retries != 0 or retry_count < max_retries:
            retry_count += 1
            if retry_count > 1:
                log.verbose("testing again")
            if self.test_connection():
                break
            else:
                log.info("Service '%s' not available", self.name)
                time.sleep(retry_interval)

    # OVERRIDE if you must close your connection
    def teardown(self, exception):
        ctx = stack.top
        if self.has_object(ref=ctx):
            # obj = self.get_object(ref=ctx)
            # obj.close()
            self.set_object(obj=None, ref=ctx)

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not self.has_object(ref=ctx):
                self.set_object(obj=self.connect(), ref=ctx)
            return self.get_object(ref=ctx)

    # OPTIONALLY
    def post_connection(self, obj=None):
        pass

    # TO BE OVERRIDDEN
    @abc.abstractmethod
    def custom_initialization(self):
        pass

    # TO BE OVERRIDDEN
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
            log.verbose("Loaded models")

    @classmethod
    def set_variables(cls, envvars):
        cls._variables = envvars

    def internal_object(self):
        return self.extension_instance.get_object()

    def configure(self, binder):

        # Get the Flask extension and its instance
        FlaskExtClass, ext_instance = self.custom_configure()
        ext_instance.injected_name = self._variables.get('injected_name')
        ext_instance.extra_service = self.extra_service

        # First connection, before any request
        ext_instance.connect()
        # And different types of initalization
        ext_instance.initialization()
        ext_instance.project_initialization()

        # Binding between the class and the instance, for Flask requests
        self.extension_instance = ext_instance
        binder.bind(FlaskExtClass, to=ext_instance, scope=self.singleton)
        return binder

    @abc.abstractmethod
    def custom_configure(self):
        return
