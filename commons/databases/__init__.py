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

    def load_base_models(self):
        module_path = 'commons.models.' + self._service_name
        module = self._meta.get_module_from_string(module_path)
        self._models_module = module_path
        models = self._meta.get_new_classes_from_module(module)
        return models

    def load_custom_models(self):
        logger.debug("TO DO")
        # # Update models module?
        # self._models_module = module_path
        return []

    def load_models(self):
        """
        Algorithm to define basic models for authorization/authentication
        and optionally let users add custom models or override existing ones.

        Important:
        This is not going to be used by the abstract class.
        The user MUST define where to load it!
        """

        # LOAD BASE MODELS
        base_models = self.load_base_models()

        # LOAD CUSTOM MODELS if file exists
        custom_models = self.load_custom_models()

        # JOIN THEM?
        self._models = base_models
        logger.debug("Loaded service models")

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
