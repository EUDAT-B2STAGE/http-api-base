# -*- coding: utf-8 -*-

""" base in common for our flask internal extensions """

# TO FIX: create a base object for flask extensions like the injector

import logging
from injector import Module, singleton


####################
# TO FIX: # how to use logs inside this extensions?
# should we make a Flask extension or a Python package out of logging?
def get_logger(name=__name__, level=logging.DEBUG):
    import logging
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
####################


class BaseInjector(Module):

    _variables = {}
    _models = {}

    def __init__(self, app):
        self.app = app
        self.singleton = singleton

    def configure(self, binder):
        # To be overidden
        return binder

    @classmethod
    def set_models(cls, models):
        cls._models = models

    @classmethod
    def set_variables(cls, envvars):
        cls._variables = envvars
