# -*- coding: utf-8 -*-

"""
to write
"""

# from __future__ import absolute_import

# import traceback
from functools import wraps
# from commons.globals import mem
# from commons.meta import Meta
from commons.logs import get_logger, pretty_print
# from flask_restful import reqparse

log = get_logger(__name__)


#################################
# TODO: make this terrible decorator disappear!
# (when completing the swagger integration)

def class_method_decorator_with_optional_parameters(f):
    """
    a decorator decorator, allowing the decorator to be used as:
    @decorator(with, arguments, and=kwargs)
    or
    @decorator
    BUT only for decorator of class methods

    Slight modifications to http://stackoverflow.com/a/14412901/2114395
    """
    @wraps(f)
    def new_dec(*args, **kwargs):
        """
        NOTE: in any case, args[0] is always the 'self' reference!
        """
        # print("DEBUG", args, kwargs)
        # log.debug("Wrapping a method decorator for double options")

        if len(args) == 2 and len(kwargs) == 0 and callable(args[1]):
            # actual decorated function
            # args[0] is self, args[1] is the function
            return f(args[0], args[1])
        elif 'from_swagger' in kwargs:
            # NOTE: the 'else' condition does not work
            # if applying the method programmatically in meta python
            return f(*args, **kwargs)
        else:
            # decorator with arguments
            # self, f, arguments
            return lambda realf: f(args[0], realf, **kwargs)

    return new_dec


#################################
# Adding a parameter to method
# ...this decorator took me quite a lot of time...

# In fact, it is a decorator which requires special points:
# 1. chaining: more than one decorator of the same type stacked
# 2. arguments: the decorator takes parameters
# 3. works for a method of class: not a single function, but with 'self'

# http://scottlobdell.me/2015/04/decorators-arguments-python/

def add_endpoint_parameters(func, parameters=[]):
                           # name, ptype=str, default=None, required=False):
    """ 
    Add a new parameter to the whole endpoint class.
    Parameters are the ones passed encoded in the url, e.g.

    GET /api/myendpoint?param1=string&param2=42

    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):

        if len(parameters) > 0:

            # Variables for debug
            class_name = self.__class__.__name__
            method_name = func.__name__.upper()

            # TO FIX: Move this Cycle into "apply_parameters"
            for parameter in parameters:
                name = parameter.get('name')
                log.debug("[Class: %s] %s decorated with parameter '%s'"
                          % (class_name, method_name, name))

#########################
                # TO FIX: Add a method to convert types swagger <-> flask
                mytype = parameter.get('type', 'string')
                if mytype == 'number':
                    mytype = int
                else:
                    mytype = str
#########################

                params = {
                    'name': name,
                    'method': method_name,
                    'mytype': mytype,
                    'default': parameter.get('default', None),
                    'required': parameter.get('required', False)
                }
                self.add_parameter(**params)

            if self.apply_parameters():
                # print("TEST", self._params)
                # from flask import request
                # pretty_print(request.__dict__)
                self.parse()

            # print("ENABLE REQUEST PARSER")
            # self._parser = reqparse.RequestParser()

        return func(self, *args, **kwargs)
    return wrapper
