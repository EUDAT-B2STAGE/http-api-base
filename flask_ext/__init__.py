# -*- coding: utf-8 -*-

""" base in common for our flask internal extensions """

# TO FIX: create a base object for flask extensions like the injector

import abc
import time
import logging
from flask import _app_ctx_stack as stack
from injector import Module, singleton
from rapydo.utils.globals import mem


####################
# TO FIX: # how to use logs inside this extensions?
# should we make a Flask extension or a Python package out of logging?
def get_logger(name=__name__, level=logging.DEBUG):
    import logging
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
####################


log = get_logger(__name__)


class BaseExtension(metaclass=abc.ABCMeta):

    def __init__(self, app=None, variables={}, models={}):

        # a different name for each extended object
        self.name = self.__class__.__name__.lower()
        log.very_verbose("Opening service instance of %s" % self.name)

        self.app = app
        if app is not None:
            self.init_app(app)

        self.models = models
        self.variables = variables
        log.very_verbose("Vars: %s" % variables)

        # for name, model in models.items():
        #     # Save attribute inside class with the same name
        #     log.verbose("Injecting model '%s'" % name)
        #     setattr(self, name, model)

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

    # TO BE OVERRIDDEN
    @abc.abstractmethod
    def custom_initialization(self):
        pass

    # TO BE OVERRIDDEN
    @abc.abstractmethod
    def custom_connection(self):
        return

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

    def teardown(self, exception):
        ctx = stack.top
        if self.has_object(ref=ctx):
            # neo does not have an 'open' connection that needs closing
            # ctx.service.close()
            self.set_object(obj=None, ref=ctx)

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not self.has_object(ref=ctx):
                self.set_object(obj=self.connect(), ref=ctx)
            return self.get_object(ref=ctx)


class BaseInjector(Module, metaclass=abc.ABCMeta):

    _models = {}
    _variables = {}
    singleton = singleton
    injected_name = 'unknown'

    def __init__(self, app):
        self.app = app

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

    def configure(self, binder):
        # Get the Flask extension and its instance
        FlaskExtClass, ext_instance = self.custom_configure()
        # Set the injected name attribute
        ext_instance.injected_name = self._variables.get('injected_name')
        # IMPORTANT: Test connection (if any)
        ext_instance.connect()
        # Save the service object into global memory...
        mem._services[ext_instance.name] = ext_instance.get_object()
        # Do initizalization for this service
        ext_instance.initialization()
        # Binding between the class and the instance, for Flask requests
        binder.bind(FlaskExtClass, to=ext_instance, scope=self.singleton)

        return binder

    @abc.abstractmethod
    def custom_configure(self):
        return
