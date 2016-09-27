# -*- coding: utf-8 -*-

""" The most standard Basic Resource i could """

import json
import pytz
from datetime import datetime
from flask import g, make_response, jsonify, Response
from flask_restful import request, Resource, reqparse
from .decorators import get_response, set_response
from ..confs.config import API_URL  # , STACKTRACE
from ..jsonify import output_json  # , RESTError
from commons import htmlcodes as hcodes
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
    _latest_headers = {}
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

        # Init for DEFAULT latest response
        self._latest_response = {
            RESPONSE_CONTENT: None,
            RESPONSE_META: None,
        }

        # Apply decision about the url of endpoint
        self.set_endpoint()
        # Make sure you can parse arguments at every call
        self._args = {}
        self._json_args = {}
        self._params = {}
        self._parser = reqparse.RequestParser()

    @staticmethod
    def clean_parameter(param=""):
        """ I get parameters already with '"' quotes from curl? """
        if param is None:
            return param
        return param.strip('"')

    def parse(self):
        """
        Parameters may be necessary at any method.
        Parse args.
        """

        self._args = self._parser.parse_args()

        # if len(self._args) < 1:
        #     try:
        #         self._args = request.get_json(force=forcing)
        #     except Exception as e:
        #         logger.warning("Fail: get JSON for current req: '%s'" % e)

        if len(self._args) > 0:
            logger.debug("Parsed parameters: %s" % self._args)

        return self._args

    def set_endpoint(self):
        if self.endpoint is None:
            self.endpoint = \
                type(self).__name__.lower().replace("resource", "")

    def get_endpoint(self):
        return (self.endpoint, self.endkey, self.endtype)

    def get_input(self, forcing=True, single_parameter=None):
        """
        Recover parameters from current requests.

        Note that we talk about JSON only when having a PUT method,
        while there is URL encoding for GET, DELETE
        and Headers encoding with POST.

        Non-JSON Parameters are already parsed at this point,
        while JSON parameters may be already saved from another previous call
        """

        # count = 0
        # for key, value in self._args.items():
        #     if value is not None:
        #         count += 1

        # if count == 0:

        if not len(self._json_args) > 0:
            try:
                self._json_args = request.get_json(force=forcing)
                for key, value in self._json_args.items():
                    if value is None:
                        continue
                    # if isinstance(value, str) and value == 'None':
                    #     continue
                    if key in self._args and self._args[key] is not None:
                        print("Key", key, "Value", value, self._args[key])
                        key += '_json'
                    self._args[key] = value
            except Exception as e:
                logger.warning("Failed to get JSON for current req: '%s'" % e)

        if single_parameter is not None:
            return self._args.get(single_parameter)

        if len(self._args) > 0:
            logger.info("Parameters %s" % self._args)
        return self._args

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
# when should I apply parameters for paging?
        # p[PERPAGE_KEY] = (int, DEFAULT_PERPAGE, False)
        # p[CURRENTPAGE_KEY] = (int, DEFAULT_CURRENTPAGE, False)
        if len(p.keys()) < 1:
            return False

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
            get_all=False, get_error=False, get_status=False, get_meta=False):

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

        content = response[RESPONSE_CONTENT]['data']
        err = response[RESPONSE_CONTENT]['errors']
        meta = response[RESPONSE_META]
        code = meta['status']

        if get_error:
            return err
        elif get_meta:
            return meta
        elif get_status:
            return code
        elif get_all:
            return content, err, code

        return content

    def set_latest_token(self, token):
## // TO FIX:
# The token should be saved into SESSION
# or this will be a global token across different users
        self.global_get('custom_auth')._latest_token = token

    def get_latest_token(self):
        return self.global_get('custom_auth')._latest_token

    def get_current_token(self):
        from ..auth import HTTPTokenAuth
        _, token = HTTPTokenAuth.get_authentication_from_headers()
        return token

    def get_current_user(self):
        """
        Return the associated User OBJECT if:
        - the endpoint requires authentication
        - a valid token was provided
        in the current endpoint call.

        Note: this method works because of actions inside
        authentication/__init__.py@verify_token method
        """

        return self.global_get('custom_auth')._user

    def global_get(self, object_name):

        obj = g.get('_%s' % object_name, None)
        if obj is None:
            raise AttributeError(
                "Global API variables: no %s object found!" % object_name)
        return obj

    def global_get_service(self,
                           service_name, object_name='services', **kwargs):

        from commons.services import get_instance_from_services
        return get_instance_from_services(
            self.global_get(object_name),   # services
            service_name,
            **kwargs)

    def method_not_allowed(self, methods=['GET']):

        methods.append('HEAD')
        methods.append('OPTIONS')
        methods_string = ""
        for method in methods:
            methods_string += method + ', '

        return self.force_response(
            headers={'ALLOW': methods_string.strip(', ')},
            errors={'message':
                    'The method is not allowed for the requested URL.'},
            code=hcodes.HTTP_BAD_METHOD_NOT_ALLOWED)

    def force_response(self, *args, **kwargs):
        method = get_response()
        return method(*args, **kwargs)

    def default_response(self, defined_content=None, elements=None,
                         code=hcodes.HTTP_OK_BASIC, errors=None, headers={}):
        """
        Handle OUR standard response following criteria described in
        https://github.com/EUDAT-B2STAGE/http-api-base/issues/7
        """

        # Avoid adding content and meta if it's already inside the data
        # In this situation probably we already called this same response
        # somewhere else
        if defined_content is not None:
            if RESPONSE_CONTENT in defined_content:
                if RESPONSE_META in defined_content:
                    # (code > 0 and code < 600):
                    return defined_content, code

        #########################
        # Compute the elements

        # Convert errors in a list, always
        if errors is not None:
            if not isinstance(errors, list):
                if not isinstance(errors, dict):
                    errors = {'Generic error': errors}
                errors = [errors]

        # Decide code range
        if errors is None and defined_content is None:
            logger.warning("RESPONSE: Warning, no data and no errors")
            code = hcodes.HTTP_OK_NORESPONSE
        elif errors is None:
            if code not in range(0, hcodes.HTTP_MULTIPLE_CHOICES):
                code = hcodes.HTTP_OK_BASIC
        elif defined_content is None:
            if code < hcodes.HTTP_BAD_REQUEST:
                # code = hcodes.HTTP_BAD_REQUEST
                code = hcodes.HTTP_SERVER_ERROR
        # else:
        #     #warnings
        #     range 300 < 400

        self._latest_response = self.make_custom_response(
            defined_content, errors, code, elements)

        return self.flask_response(
            data=self._latest_response, status=code, headers=headers)

    @staticmethod
    def make_custom_response(
            defined_content=None, errors=None, code=None, elements=None):
        """
        Try conversions and compute types and length
        """
        try:
            data_type = str(type(defined_content))
            if elements is None:
                if defined_content is None:
                    elements = 0
                elif isinstance(defined_content, str):
                    elements = 1
                else:
                    elements = len(defined_content)

            if errors is None:
                total_errors = 0
            else:
                total_errors = len(errors)

            code = int(code)
        except Exception as e:
            logger.critical("Could not build response!\n%s" % e)
            # Revert to defaults
            defined_content = None,
            data_type = str(type(defined_content))
            elements = 0
            # Also set the error
            code = hcodes.HTTP_SERVICE_UNAVAILABLE
            errors = [{'Failed to build response': str(e)}]
            total_errors = len(errors)

        # Note: latest_response is an attribute
        # of an object instance created per request
        return {
            RESPONSE_CONTENT: {
                'data': defined_content,
                'errors': errors,
            },
            RESPONSE_META: {
                'data_type': data_type,
                'elements': elements,
                'errors': total_errors,
                'status': code
            }
        }

    def empty_response(self):
        return self.force_response("", code=hcodes.HTTP_OK_NORESPONSE)

    def report_generic_error(self,
                             message=None, current_response_available=True):

        if message is None:
            message = "Something BAD happened somewhere..."
        logger.critical(message)

        user_message = "Server unable to respond."
        code = hcodes.HTTP_SERVER_ERROR
        if current_response_available:
            return self.force_response(user_message, code=code)
        else:
            return self.flask_response(user_message, status=code)

    @staticmethod
    def check_response(response):
        return isinstance(response, Response)

    @staticmethod
    def flask_response(data, status=hcodes.HTTP_OK_BASIC, headers={}):
        """
        Inspired by
        http://blog.miguelgrinberg.com/
            post/customizing-the-flask-response-class

        Every default/custom response should use this in the end
        """

        # Handle normal response (not Flaskified)
        if isinstance(data, tuple) and len(data) == 2:
            subdata, substatus = data
            data = subdata
            if isinstance(substatus, int):
                status = substatus

        # Create the Flask original response
        response = make_response((jsonify(data), status))

        # Handle headers if specified by the user
        response_headers = response.headers.keys()
        for header, header_content in headers.items():
            # Only headers that are missing
            if header not in response_headers:
                response.headers[header] = header_content

        return response

    @staticmethod
    def timestamp_from_string(timestamp_string):
        """
        Neomodels complains about UTC, this is to fix it.
        Taken from http://stackoverflow.com/a/21952077/2114395
        """

        precision = float(timestamp_string)
        # return datetime.fromtimestamp(precision)

        utc_dt = datetime.utcfromtimestamp(precision)
        aware_utc_dt = utc_dt.replace(tzinfo=pytz.utc)

        return aware_utc_dt

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

    def getJsonResponse(self, instance,
                        fields=[], resource_type=None, skip_missing_ids=False,
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
            "links": {"self": request.url + '/' + id},
        }

        if skip_missing_ids and id == '-':
            del data['id']

## // TO FIX:
        # Difficult task for now to compute links ID for relationships
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
                                skip_missing_ids=skip_missing_ids,
                                relationship_depth=relationship_depth + 1,
                                max_relationship_depth=max_relationship_depth))

                linked[relationship] = subrelationship

            if len(linked) > 0:
                data['relationships'] = linked

        return data

# Set default response
set_response(
    original=False,  # first_call=True,
    custom_method=ExtendedApiResource().default_response)
