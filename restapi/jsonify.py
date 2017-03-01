# -*- coding: utf-8 -*-

"""
Specialized JSON-oriented Flask App.

Why?
When things go wrong, default errors that Flask/Werkzeug respond are all HTML.
Which breaks the clients who expect JSON back even in case of errors.

source: http://flask.pocoo.org/snippets/83/
"""

# from __future__ import absolute_import

# from flask import jsonify, make_response
# from werkzeug.exceptions import HTTPException
from restapi.utils import htmlcodes as hcodes
from restapi.utils import json

# from restapi.utils.logs import get_logger
# log = get_logger(__name__)


def test_json(message):
    return json(message)


##############################

# def make_json_error(ex):

# Could this be moved/improved?
# see http://flask.pocoo.org/snippets/20/

#     response = jsonify(message=str(ex))
#     response.status_code = \
#         (ex.code
#             if isinstance(ex, HTTPException)
#             else hcodes.HTTP_SERVER_ERROR)
#     return response


####################################
# Custom error handling: SAVE TO LOG
# http://flask-restful.readthedocs.org/en/latest/
# extending.html#custom-error-handlers

# def log_exception(sender, exception, **extra):
#     """ Log an exception to our logging framework """
#     sender.log.error(
#         'Got exception during processing:' +
#         '\nSender "%s"\nException "%s"' % (sender, exception))


##############################
# My rest exception class, extending Flask
# http://flask.pocoo.org/docs/0.10/patterns/apierrors/#simple-exception-class
class RESTError(Exception):

    status_code = hcodes.HTTP_BAD_REQUEST

    def __init__(self, message, status_code=None, payload=None):
        # My exception
        Exception.__init__(self)
        # Variables
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
