# -*- coding: utf-8 -*-

""" The most standard Basic Resource i could """

from .. import htmlcodes as hcodes
# from confs.config import STACKTRACE
from confs.config import API_URL
from ..jsonify import output_json  # , RESTError
from flask import make_response, jsonify
from flask.ext.restful import request, Resource, reqparse
from .. import get_logger

logger = get_logger(__name__)

CURRENTPAGE_KEY = 'currentpage'
DEFAULT_CURRENTPAGE = 1
PERPAGE_KEY = 'perpage'
DEFAULT_PERPAGE = 10

RESPONSE_CONTENT = "Response"
RESPONSE_META = "Meta"


# Extending the concept of rest generic resource
class ExtendedApiResource(Resource):
    """ Implement a generic Resource for Restful model """

    myname = __name__
    _args = {}
    _params = {}
    endtype = None
    endpoint = None
    hcode = hcodes.HTTP_OK_BASIC
    base_url = API_URL

    def __init__(self):
        super(ExtendedApiResource, self).__init__()
# NOTE: you can add as many representation as you want!
        self.representations = {
            # Be sure of handling JSON
            'application/json': output_json,
        }
        # Init for latest response
        self._latest_response = {
            RESPONSE_CONTENT: None,
            RESPONSE_META: None,
        }
        # Apply decision about the url of endpoint
        self.set_endpoint()
        # Make sure you can parse arguments at every call
        self._parser = reqparse.RequestParser()

    @staticmethod
    def clean_parameter(param=""):
        """ I get parameters already with '"' quotes from curl? """
        if param is None:
            return param
        return param.strip('"')

    def parse(self):
        """ Parameters may be necessary at any method """
        self._args = self._parser.parse_args()
        logger.debug("Received parameters: %s" % self._args)

    def set_endpoint(self):
        if self.endpoint is None:
            self.endpoint = \
                type(self).__name__.lower().replace("resource", "")

    def get_endpoint(self):
        return (self.endpoint, self.endtype)

    def get_input(self, forcing=True):
        """ Get JSON. The power of having a real object in our hand. """
        return request.get_json(force=forcing)

    def myname(self):
        return self.__class__.__name__

    def add_parameter(self, name, mytype=str, default=None, required=False):
        """ Save a parameter inside the class """
        # Class name as a key
        key = self.myname()
        if key not in self._params:
            self._params[key] = {}
        # Avoid if already exists?
        if name not in self._params[key]:
            self._params[key][name] = [mytype, default, required]

    def apply_parameters(self):
        """ Use parameters received via decoration """

        key = self.myname()
        if key not in self._params:
            return False

        ##############################
        # Basic options
        basevalue = str  # Python3
        # basevalue = unicode  #Python2
        act = 'store'  # store is normal, append is a list
        loc = ['headers', 'values']  # multiple locations
        trim = True

# // TO FIX?
        self._params[key][PERPAGE_KEY] = (int, DEFAULT_PERPAGE, False)
        self._params[key][CURRENTPAGE_KEY] = (int, DEFAULT_CURRENTPAGE, False)

        for param, \
            (param_type, param_default, param_required) in \
                self._params[key].items():

            # Decide what is left for this parameter
            if param_type is None:
                param_type = basevalue

            # I am creating an option to handle arrays:
            if param_type == 'makearray':
                param_type = basevalue
                act = 'append'

            # Really add the parameter
            self._parser.add_argument(
                param, type=param_type,
                default=param_default, required=param_required,
                trim=trim, action=act, location=loc)
            logger.info("Accept param '%s', type %s" % (param, param_type))

        return True

    def set_method_id(self, name='myid', idtype='string'):
        """ How to have api/method/:id route possible"""
        self.endtype = idtype + ':' + name

    def get_paging(self):
        limit = self._args.get(PERPAGE_KEY, DEFAULT_PERPAGE)
        current_page = self._args.get(CURRENTPAGE_KEY, DEFAULT_CURRENTPAGE)
        return (current_page, limit)

    def get_content_from_response(
            self, http_out=None,
            get_error=False, get_status=False, get_meta=False):

        if http_out is None:
            http_out = self._latest_response

        if not isinstance(http_out, tuple) or len(http_out) != 2:
            raise ValueError(
                "Trying to recover informations" +
                " from a malformed response:\n%s" % http_out)

        response, status = http_out

        if get_error:
            return response[RESPONSE_CONTENT]['errors']
        elif get_meta:
            return response[RESPONSE_META]
        elif get_status:
            return response[RESPONSE_META]['status']

        return response[RESPONSE_CONTENT]['data']

    def global_get(self, object_name):

        from flask import g
        obj = g.get('_' + object_name, None)
        if obj is None:
            return self.response(
                errors={"Internal error": "No %s object found!" % object_name},
                code=hcodes.HTTP_BAD_CONFLICT)
        return obj

    def global_get_service(self,
                           service_name, object_name='services', **kwargs):

        services = self.global_get(object_name)
        obj = services.get(service_name, None)
        if obj is None:
            return self.response(
                errors={
                    "Internal error": "No %s service found!" % service_name},
                code=hcodes.HTTP_BAD_CONFLICT)
        return obj().get_instance(**kwargs)

    def response(self, data=None, elements=None,
                 errors=None, code=hcodes.HTTP_OK_BASIC, headers={}):
        """
        Handle a standard response following criteria described in
        https://github.com/EUDAT-B2STAGE/http-api-base/issues/7
        """

        # Skip this method if the whole data
        # is already a Flask Response
        from werkzeug.wrappers import Response
        if isinstance(data, Response):
            return data

        # Do not apply if the object has already been used
        # as a 'standard response' from a parent call
        existing_content = {}
        existing_code = hcodes.HTTP_OK_BASIC

        # print("Tuple?", data, isinstance(data, tuple), len(data))

        # Normal response
        if isinstance(data, tuple) and len(data) == 2:
            existing_content, existing_code = data
            # print("Received", existing_content, existing_code)

        # Missing code in response
        if isinstance(data, dict) and len(data) == 2:
            existing_content = data
            if RESPONSE_META in existing_content:
                existing_code = existing_content[RESPONSE_META]['status']

        if RESPONSE_CONTENT in existing_content \
           and RESPONSE_META in existing_content:
            if existing_code > 0 and existing_code < 600:
                return existing_content, existing_code

        #########################
        # Compute the elements

        # Convert errors in a list, always
        if errors is not None:
            if not isinstance(errors, list):
                if not isinstance(errors, dict):
                    errors = {'Generic error': errors}
                errors = [errors]

        # Decide code range
        if errors is None and data is None:
            logger.warning("RESPONSE: Warning, no data and no errors")
            code = hcodes.HTTP_OK_NORESPONSE
        elif errors is None:
            if code not in range(0, hcodes.HTTP_MULTIPLE_CHOICES):
                code = hcodes.HTTP_OK_BASIC
        elif data is None:
            if code < hcodes.HTTP_BAD_REQUEST:
                code = hcodes.HTTP_BAD_REQUEST
        # else:
        #     #warnings
        #     range 300 < 400

        # Try conversions and compute types and length
        try:
            data_type = str(type(data))
            if elements is None:
                if data is None:
                    elements = 0
                elif isinstance(data, str):
                    elements = 1
                else:
                    elements = len(data)

            if errors is None:
                total_errors = 0
            else:
                total_errors = len(errors)

            code = int(code)
        except Exception as e:
            logger.critical("Could not build response: %s" % e)
            # Revert to defaults
            data = None,
            data_type = str(type(data))
            elements = 0
            # Also set the error
            code = hcodes.HTTP_SERVICE_UNAVAILABLE
            errors = [{'Failed to build response': str(e)}]
            total_errors = len(errors)

        self._latest_response = {
            RESPONSE_CONTENT: {
                'data': data,
                'errors': errors,
            },
            RESPONSE_META: {
                'data_type': data_type,
                'elements': elements,
                'errors': total_errors,
                'status': code
            }
        }

        ########################################
        # Make a Flask Response
        # http://blog.miguelgrinberg.com/
        # # post/customizing-the-flask-response-class
        response = make_response(
            (jsonify(self._latest_response), code))

        response_headers = response.headers.keys()
        for header, header_content in headers.items():
            if header not in response_headers:
                response.headers[header] = header_content

        return response
