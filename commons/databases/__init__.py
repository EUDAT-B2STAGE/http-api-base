# -*- coding: utf-8 -*-

"""

This class should help creating Farm of any database/service instance
to be used inside a Flask server.

The idea is to have the connection check when the Farm class is instanciated.
Then the object would remain available inside the server global namespace
to let the user access a new connection.

"""

from __future__ import absolute_import
import abc
import time
import logging
from ..meta import Meta

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_MODELS_PATH = 'commons.models.'


class DBinstance(metaclass=abc.ABCMeta):

    _meta = Meta()
    _service_name = None
    _models = {}
    _models_module = None

    def __init__(self, check_connection=False, app=None):

        self._service_name = self.define_service_name()

        if not check_connection:
            return

        name = self.__class__.__name__
        testdb = True
        counter = 0
        sleep_time = 1

        while testdb:
            try:
                obj = self.init_connection(app)
                del obj
                testdb = False
                logger.info("Instance of '%s' was connected" % name)
            except AttributeError as e:
                # Give the developer a way to stop this cycle if critical
                raise e
            except Exception as e:
                counter += 1
                if counter % 5 == 0:
                    sleep_time += sleep_time * 2
                logger.warning("%s: Not reachable yet. Sleeping %s."
                               % (name, sleep_time))
                logger.debug("Error was %s" % str(e))
                time.sleep(sleep_time)

    def load_generic_models(self, module_path):
        module = self._meta.get_module_from_string(module_path)
        models = self._meta.get_new_classes_from_module(module)
        # Keep tracking from where we loaded models
        # This may help with some service (e.g. sqlalchemy)
        self._models_module = module_path
        return models

    def load_base_models(self):
        module_path = BASE_MODELS_PATH + self._service_name
        logger.debug("Loading base models")
        return self.load_generic_models(module_path)

    def load_custom_models(self):
        module_path = BASE_MODELS_PATH + 'custom.' + self._service_name
        logger.debug("Loading custom models")
        return self.load_generic_models(module_path)

    def load_models(self):
        """
        Algorithm to define basic models for authorization/authentication
        and optionally let users add custom models or override existing ones.

        Important:
        This is not going to be used by the abstract class.
        The user MUST define where to load it!
        """

        # Load base models
        base_models = self.load_base_models()
        # Load custom models, if the file exists
        custom_models = self.load_custom_models()

        # Join models as described by issue #16
        self._models = base_models
        for key, model in custom_models.items():
            # Verify if overriding
            if key in base_models.keys():
                original_model = base_models[key]
                # Override
                if issubclass(model, original_model):
                    logger.debug("Overriding model %s" % key)
                    self._models[key] = model
                    continue
            # Otherwise just append
            self._models[key] = model

        logger.debug("Loaded service models")
        return self._models

    @abc.abstractmethod
    def define_service_name(self):
        """
        Please define a name for the current implementation
        """
        return

    @abc.abstractmethod
    def init_connection(self, app):
        return

    @abc.abstractmethod
    def get_instance(self, *args):
        return
