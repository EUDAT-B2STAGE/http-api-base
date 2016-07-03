# -*- coding: utf-8 -*-

""" The most standard Basic Resource i could """

from commons import htmlcodes as hcodes
from ..confs.config import API_URL  # , STACKTRACE
from ..jsonify import output_json  # , RESTError
from flask import make_response, jsonify, g, Response
from flask_restful import request, Resource, reqparse
import json
from datetime import datetime
from commons.logs import get_logger

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
    endpoint = None
    endkey = None
    endtype = None
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
        return (self.endpoint, self.endkey, self.endtype)

    def get_input(self, forcing=True):
        """ Get JSON. The power of having a real object in our hand. """
        return request.get_json(force=forcing)

    def myname(self):
        return self.__class__.__name__

    def add_parameter(self, name, method,
                      mytype=str, default=None, required=False):
        """ Save a parameter inside the class """

        # Class name as a key
        key = self.myname()

        if key not in self._params:
            self._params[key] = {}

        if method not in self._params[key]:
            self._params[key][method] = {}

        # Avoid if already exists?
        if name not in self._params[key][method]:
            self._params[key][method][name] = [mytype, default, required]

    def apply_parameters(self, method):
        """ Use parameters received via decoration """

        key = self.myname()
        if key not in self._params:
            return False

        if method not in self._params[key]:
            return False

        p = self._params[key][method]

        ##############################
        # Basic options
        basevalue = str  # Python3
        # basevalue = unicode  #Python2
        act = 'store'  # store is normal, append is a list
        loc = ['headers', 'values']  # multiple locations
        trim = True

# // TO FIX?
        p[PERPAGE_KEY] = (int, DEFAULT_PERPAGE, False)
        p[CURRENTPAGE_KEY] = (int, DEFAULT_CURRENTPAGE, False)

        for param, (param_type, param_default, param_required) in p.items():

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

        try:
            response = json.loads(http_out.get_data().decode())
        except Exception as e:
            logger.critical("Failed to load response:\n%s" % e)
            raise ValueError(
                "Trying to recover informations" +
                " from a malformed response:\n%s" % http_out)

        if not isinstance(response, dict) or len(response) != 2:
            raise ValueError(
                "Trying to recover informations" +
                " from a malformed response:\n%s" % response)

        if get_error:
            return response[RESPONSE_CONTENT]['errors']
        elif get_meta:
            return response[RESPONSE_META]
        elif get_status:
            return response[RESPONSE_META]['status']

        return response[RESPONSE_CONTENT]['data']

    def set_latest_token(self, token):
        self.global_get('custom_auth')._latest_token = token
## // TO FIX:
# The token should be saved into SESSION
# or this will be a global token across different users

    def get_latest_token(self):
        return self.global_get('custom_auth')._latest_token

    def get_current_token(self):
        from ..auth import HTTPTokenAuth
        _, token = HTTPTokenAuth.get_authentication_from_headers()
        return token

    def global_get(self, object_name):

        obj = g.get('_%s' % object_name, None)
        if obj is None:
            raise AttributeError(
                "Global API variables: no %s object found!" % object_name)
        return obj

    def global_get_service(self,
                           service_name, object_name='services', **kwargs):

        services = self.global_get(object_name)
        obj = services.get(service_name, None)
        if obj is None:
            raise AttributeError(
                "Global API services: '%s' not found!" % service_name)
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

        # Normal response
        if isinstance(data, tuple) and len(data) == 2:
            existing_content, existing_code = data

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

# UHM
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

    def formatJsonResponse(self, instances, resource_type=None):
        """
            Format specifications can be found here:
            http://jsonapi.org
        """

        json_data = {}
        endpoint = request.url
        json_data["links"] = {
            "self": endpoint,
            "next": None,
            "last": None,
        }

        json_data["content"] = []
        if not isinstance(instances, list):
            raise AttributeError("Expecting a list of objects to format")
        if len(instances) < 1:
            return json_data

        for instance in instances:
            json_data["content"].append(self.getJsonResponse(instance))

## // TO FIX:
# get pages FROM SELF ARGS?
        # json_data["links"]["next"] = \
        #     endpoint + '?currentpage=2&perpage=1',
        # json_data["links"]["last"] = \
        #     endpoint + '?currentpage=' + str(len(instances)) + '&perpage=1',

        return json_data

    def getJsonResponse(self, instance, fields=[], resource_type=None,
                        relationship_depth=0, max_relationship_depth=1):
        """
        Lots of meta introspection to guess the JSON specifications
        """

        if resource_type is None:
            resource_type = type(instance).__name__.lower()

        # Get id
        verify_attribute = hasattr
        if isinstance(instance, dict):
            verify_attribute = dict.get
        if verify_attribute(instance, "id"):
            id = instance.id
        else:
            # Do not show internal id. Only UUID if available.
            id = "-"

        data = {
            "id": id,
            "type": resource_type,
            "attributes": {},
## // TO FIX:
            # Very difficult for relationships
            "links": {"self": request.url + '/' + id},
        }

        if relationship_depth > 0:
            del data['links']

        # Attributes
        if len(fields) < 1 and hasattr(instance, '_fields_to_show'):
            fields = getattr(instance, '_fields_to_show')

        for key in fields:
            if verify_attribute(instance, key):
                get_attribute = getattr
                if isinstance(instance, dict):
                    get_attribute = dict.get

                attribute = get_attribute(instance, key)
                # datetime is not json serializable,
                # converting it to string
## // TO FIX:
# use flask.jsonify
                if isinstance(attribute, datetime):
                    data["attributes"][key] = attribute.strftime('%s')
                else:
                    data["attributes"][key] = attribute

        # Relationships
        if relationship_depth < max_relationship_depth:
            linked = {}
            relationships = []
            if hasattr(instance, '_relationships_to_follow'):
                relationships = getattr(instance, '_relationships_to_follow')
            for relationship in relationships:
                subrelationship = []
                # logger.debug("Investigate relationship %s" % relationship)

                if hasattr(instance, relationship):
                    for node in getattr(instance, relationship).all():
                        subrelationship.append(
                            self.getJsonResponse(
                                node,
                                relationship_depth=relationship_depth + 1,
                                max_relationship_depth=max_relationship_depth))

                linked[relationship] = subrelationship

            if len(linked) > 0:
                data['relationships'] = linked

        return data
