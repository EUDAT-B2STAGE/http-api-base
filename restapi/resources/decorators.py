# -*- coding: utf-8 -*-

"""

Decorating my REST API resources.

Decorate is a cool but sometimes dangerous place in Python, I guess.
Here we test different kind of decorations for different problems.

Restful resources are Flask Views classes.
Official docs talks about their decoration:
http://flask-restful.readthedocs.org/en/latest/extending.html#resource-method-decorators
So... you should also read better this section of Flask itself:
http://flask.pocoo.org/docs/0.10/views/#decorating-views

I didn't manage so far to have it working in the way the documentation require.

"""

from __future__ import absolute_import

# import traceback
from functools import wraps
from commons import htmlcodes as hcodes
from commons.globals import mem
from commons.logs import get_logger
from commons.meta import Meta

from .. import myself, lic

__author__ = myself
__copyright__ = myself
__license__ = lic

log = get_logger(__name__)


#################################
# Identity is usefull to some (very) extreme decorators cases
def identity(*args, **kwargs):
    """
    Expecting no keywords arguments
    """
    kwargs['content'] = args
## TO CHECK AGAIN
    return kwargs


#################################
# Decide what is the response method for every endpoint

def set_response(original=False, custom_method=None, first_call=False):

    # Use identity if requested
    if original:
        mem.current_response = identity

    # Custom method is another option
    elif custom_method is not None:
        mem.current_response = custom_method

        # Debug when response is injected and if custom
        if not first_call:
            log.debug("Response method set to: %s" % custom_method)


def custom_response(func=None, original=False):
    set_response(original=original, custom_method=func)


def get_response():
    return mem.current_response


#################################
# Adding an identifier to a REST class
# https://andrefsp.wordpress.com/2012/08/23/writing-a-class-decorator-in-python

def enable_endpoint_identifier(name='myid', idtype='string'):
    """
    Class decorator for ExtendedApiResource objects;
    Enable identifier and let you choose name and type.
    """
    def class_rebuilder(cls):   # decorator

        def init(self):
            log.info("[%s] Applying ID to endopoint:%s of type '%s'"
                     % (self.__class__.__name__, name, idtype))
            self.set_method_id(name, idtype)
            # log.debug("New init %s %s" % (name, idtype))
            super(cls, self).__init__()

        NewClass = Meta.metaclassing(
            cls, cls.__name__ + '_withid', {'__init__': init})
        return NewClass
    return class_rebuilder


#################################
# TOFIX: remove it here, it has been moved to commons
def add_endpoint_parameter(name, ptype=str, default=None, required=False):

    def decorator(func):
        log.warning("DEPRECATED add_endpoint_parameter for %s" % func)

        @wraps(func)
        def wrapper(self, *args, **kwargs):

            class_name = self.__class__.__name__
            method_name = func.__name__.upper()
            log.debug("[Class: %s] %s decorated with parameter '%s'"
                      % (class_name, method_name, name))
            params = {
                'name': name,
                'method': method_name,
                'mytype': ptype,
                'default': default,
                'required': required,
            }
            self.add_parameter(**params)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


##############################
# Defining a generic decorator for restful methods

# It will assure to have all necessary things up:

# 1. standard json data returns
# MOVED INTO response.py/server.py

# 2. also to have my requested parameters configured and parsed
# right before the function call (necessary for flask_restful)
# http://flask-restful.readthedocs.org/en/latest/reqparse.html

def apimethod(func):
# TODO: remove it when nobody uses it anymore
    """ 
    Decorate methods to return the most standard json data
    and also to parse available args before using them in the function
    """

    log.warning("Deprecated 'apimethod', to add parameters use SWAGGER")

    @wraps(func)
    def wrapper(self, *args, **kwargs):

        # Debug
        class_name = self.__class__.__name__
        method_name = func.__name__.upper()
        log.info("[Class: %s] %s request" % (class_name, method_name))

        #######################
        # PARAMETERS INPUT

        # Load the right parameters that were decorated
        if self.apply_parameters(method_name):
            # Call the parse method
            self.parse()

        #######################
        # Call the wrapped function
        out = None
        try:
            out = func(self, *args, **kwargs)
        # Handle any error to avoid Flask using the HTML web page for errors
        except BaseException as e:
            # raise e
            log.warning("nb: dig more changing the decorator 'except'")
            # import sys
            # error = sys.exc_info()[0]

            # If we raise NotImpleted ...
            if isinstance(e, NotImplementedError):
                message = "Missing functionality"
            else:
                message = "Unexpected error"
            return self.report_generic_error("%s\n[%s]" % (message, e))

# #######################
# # TO CHECK AND PROBABLY REMOVE
#         except TypeError as e:
#             log.warning(e)
#             error = str(e).strip("'")
#             log.critical("Type error: %s" % error)

#             # This error can be possible only if using the default response
#             if "required positional argument" in error:
#                 return self.report_generic_error(
#                     "Custom response defined is not compliant",
#                     current_response_available=False)
#             raise e
        finally:
            log.debug("Called %s", func)

        return out

    return wrapper


##############################
# A decorator for the whole class

"""
def time_all_class_methods(Cls):
    class NewCls(object):
        def __init__(self,*args,**kwargs):
            self.oInstance = Cls(*args,**kwargs)

"""


def all_rest_methods(Cls):
# TODO: remove it when nobody uses 'apimethod' anymore
    """
    Decorate all the rest methods inside the custom restful class,
    with the previously created 'apimethod'
    """

    api_methods = ['get', 'post', 'put', 'patch', 'delete']  # , 'search']

    for attr in Cls.__dict__:

        # Check if it's a method and if in it's in my list
        if attr not in api_methods or not callable(getattr(Cls, attr)):
            continue

        # Get the method, and set the decorated version
        original_method = getattr(Cls, attr)
        setattr(Cls, attr, apimethod(original_method))

        log.debug("Decorated %s.%s as api method" % (Cls.__name__, attr))

    return Cls


#####################################################################
# Error handling with custom methods
def exceptionError(self, label, e, code):
    error = str(e)
    log.error(error)
    return self.send_errors(label, error, code=code)


def error_handler(func, self, some_exception,
                  label, catch_generic, error_code, args, kwargs):

    out = None
    # print(func, self, some_exception, label, args, kwargs)
    default_label = 'Server error'
    if label is None:
        label = default_label
    try:
        out = func(self, *args, **kwargs)
    # Catch the single exception that the user requested
    except some_exception as e:
        return exceptionError(self, label, e, error_code)
# TODO: check with @mdantonio
    # except Exception as e:
    #     log.warning(
    #         "Unexpected exception inside error handler:\n%s" % str(e))

    #     if not catch_generic:
    #         raise e
    #     else:
    #         traceback.print_exc()
    #         return exceptionError(
    #             self, default_label, 'Please contact service administrators',
    #             code=hcodes.HTTP_SERVER_ERROR)
    else:
        pass

    return out


def catch_error(
        exception=None, exception_label=None,
        catch_generic=True, error_code=hcodes.HTTP_BAD_REQUEST):
    """
    A decorator to preprocess an API class method,
    and catch a specific error.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return error_handler(
                func, self,
                exception, exception_label, catch_generic, error_code,
                args, kwargs)
        return wrapper
    return decorator
