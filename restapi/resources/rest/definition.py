# -*- coding: utf-8 -*-

"""
The most basic (and standard) Rest Resource
we could provide back then
"""

from __future__ import absolute_import

import pytz
import dateutil.parser
from datetime import datetime
from flask import g
from flask_restful import request, Resource, reqparse

from ...confs.config import API_URL  # , STACKTRACE
from ...response import ResponseElements
from commons import htmlcodes as hcodes
from commons.logs import get_logger

logger = get_logger(__name__)

###################
# Paging costants
CURRENTPAGE_KEY = 'currentpage'
DEFAULT_CURRENTPAGE = 1
PERPAGE_KEY = 'perpage'
DEFAULT_PERPAGE = 10


###################
# Extending the concept of rest generic resource

class EndpointResource(Resource):
    """
    Implements a generic Resource for our Restful APIs model
    """

    myname = __name__
    _latest_headers = {}
    endpoint = None
    endkey = None
    endtype = None
    hcode = hcodes.HTTP_OK_BASIC
    base_url = API_URL

    def __init__(self):
        super(EndpointResource, self).__init__()

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
        # if self.endpoint is None:
        #     self.endpoint = \
        #         type(self).__name__.lower().replace("resource", "")
        pass

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

        if len(self._json_args) < 1:
            try:
                self._json_args = request.get_json(force=forcing)
                for key, value in self._json_args.items():
                    if value is None:
                        continue
                    # if isinstance(value, str) and value == 'None':
                    #     continue
                    if key in self._args and self._args[key] is not None:
                        # print("Key", key, "Value", value, self._args[key])
                        key += '_json'
                    self._args[key] = value
            except Exception:  # as e:
                # logger.critical("Cannot get JSON for req: '%s'" % e)
                pass

        if single_parameter is not None:
            return self._args.get(single_parameter)

        if len(self._args) > 0:
            logger.info("Parameters %s" % self._args)
        return self._args

    def myname(self):
        return self.__class__.__name__

    def add_parameter(self, name, method,
                      mytype=str, default=None, required=False):
        """
        Save a parameter inside the class

        Note: parameters are specific to the method
        (and not to the whole class as before) using subarrays
        """

        # Class name as a key
        classname = self.myname()

        if classname not in self._params:
            self._params[classname] = {}

        if method not in self._params[classname]:
            self._params[classname][method] = {}

        # Avoid if already exists?
        if name not in self._params[classname][method]:
            self._params[classname][method][name] = [mytype, default, required]

    def apply_parameters(self, method):
        """ Use parameters received via decoration """

        classname = self.myname()
        if classname not in self._params:
            return False
        if method not in self._params[classname]:
            return False
        p = self._params[classname][method]

        ##############################
        # Basic options
        basevalue = str  # Python3
        # basevalue = unicode  #Python2
        act = 'store'  # store is normal, append is a list
        loc = ['headers', 'values']  # multiple locations
        trim = True

## // TO FIX?
# when should I apply parameters for paging?
# let the developer specify with a dedicated decorator?
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
            logger.debug("Accept param '%s', type %s" % (param, param_type))

        return True

    def set_method_id(self, name='myid', idtype='string'):
        """ How to have api/method/:id route possible"""
        self.endtype = idtype + ':' + name

    def get_paging(self):
        limit = self._args.get(PERPAGE_KEY, DEFAULT_PERPAGE)
        current_page = self._args.get(CURRENTPAGE_KEY, DEFAULT_CURRENTPAGE)
        return (current_page, limit)

    def explode_response(self,
                         api_output, get_all=False,
                         get_error=False, get_status=False, get_meta=False):

        from ..response import get_content_from_response
        content, err, meta, code = get_content_from_response(api_output)

        if get_error:
            return err
        elif get_meta:
            return meta
        elif get_status:
            return code
        elif get_all:
            return content, err, code

        return content

# BAD PRACTICE
    # def set_latest_token(self, token):
    #     self.global_get('custom_auth')._latest_token = token

    # def get_latest_token(self):
    #     return self.global_get('custom_auth')._latest_token
# BAD PRACTICE

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

        return self.global_get('custom_auth').get_user()

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
## IS IT USED?

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
        """
        Helper function to let the developer define
        how to respond with the REST and HTTP protocol

        Build a ResponseElements instance.
        """
        # logger.debug("Force response:\nargs[%s] kwargs[%s]" % (args, kwargs))

        # If args has something, it should be one simple element
        # That element is the content and nothing else
        if isinstance(args, tuple) and len(args) > 0:
            kwargs['defined_content'] = args[0]
        elif 'defined_content' not in kwargs:
            kwargs['defined_content'] = None

        # try to push keywords arguments directly to the attrs class
        response = None
        try:
            response = ResponseElements(**kwargs)
        except Exception as e:
            response = ResponseElements(errors=str(e))
        return response

    def empty_response(self):
        """ Empty response as defined by the protocol """
        return self.force_response("", code=hcodes.HTTP_OK_NORESPONSE)

    def send_warnings(self, defined_content, errors, code=None):
        """
        Warnings when there is both data and errors in response.
        So 'defined_content' and 'errors' are required,
        while the code has to be between below 400
        """
        if code is None or code >= hcodes.HTTP_BAD_REQUEST:
            code = hcodes.HTTP_MULTIPLE_CHOICES

        return self.force_response(
            defined_content=defined_content, errors=errors, code=code)

    def send_errors(self, label="Error", message=None, errors=None, code=None):
        """
        Setup an error message and
        """

        # Bug fix: if errors was initialized above, I received old errors...
        if errors is None:
            errors = {}

        # See if we have the main message
        error = {}
        if message is not None:
            error = {label: message}

        # Extend existing errors
        if isinstance(errors, dict) and len(error) > 0:
            errors.update(error)

        if code is None or code < hcodes.HTTP_BAD_REQUEST:
            # default error
            code = hcodes.HTTP_SERVER_ERROR

        return self.force_response(errors=errors, code=code)

    def report_generic_error(self,
                             message=None, current_response_available=True):

        if message is None:
            message = "Something BAD happened somewhere..."
        logger.critical(message)

        user_message = "Server unable to respond."
        code = hcodes.HTTP_SERVER_ERROR
        if current_response_available:
            return self.force_response(errors=user_message, code=code)
        else:
            # flask-like
            return (user_message, code)

    def send_crentials(self, token, extra=None, meta=None):
        """
        Define a standard response to give a Bearer token back.
        Also considering headers.
        """
## // TO FIX
        return NotImplementedError("To be written")

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
    @staticmethod
    def dateFromString(date, format="%d/%m/%Y"):

        if date == "":
            return ""
        # datetime.now(pytz.utc)
        try:
            return datetime.strptime(date, format)
        except:
            return dateutil.parser.parse(date)

    @staticmethod
# To mattia: can we stop using java-like camelCase? XD
    def stringFromTimestamp(timestamp):
        if timestamp == "":
            return ""
        try:
            date = datetime.fromtimestamp(float(timestamp))
            return date.isoformat()
        except:
            logger.warning(
                "Errors parsing %s" % timestamp)
            return ""

    def getJsonResponse(self, instance,
                        fields=[], resource_type=None, skip_missing_ids=False,
                        only_public=False,
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
        if verify_attribute(instance, "uuid"):
            id = instance.uuid
        elif verify_attribute(instance, "id"):
            id = instance.id
        else:
            # Do not show internal id. Only UUID if available.
            id = "-"

        if id is None:
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
        if len(fields) < 1:

            if only_public:
                field_name = '_public_fields_to_show'
            else:
                field_name = '_fields_to_show'

            if hasattr(instance, field_name):
                fields = getattr(instance, field_name)

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
                if attribute is None:
                    data["attributes"][key] = ""
                elif isinstance(attribute, datetime):
                    dval = self.stringFromTimestamp(attribute.strftime('%s'))
                    data["attributes"][key] = dval
                else:
                    data["attributes"][key] = attribute

        # Relationships
        if relationship_depth < max_relationship_depth:
            linked = {}
            relationships = []
            if only_public:
                field_name = '_public_relationships_to_follow'
            else:
                field_name = '_relationships_to_follow'
            if hasattr(instance, field_name):
                relationships = getattr(instance, field_name)

            for relationship in relationships:
                subrelationship = []
                # logger.debug("Investigate relationship %s" % relationship)

                if hasattr(instance, relationship):
                    for node in getattr(instance, relationship).all():
                        subrelationship.append(
                            self.getJsonResponse(
                                node,
                                only_public=only_public,
                                skip_missing_ids=skip_missing_ids,
                                relationship_depth=relationship_depth + 1,
                                max_relationship_depth=max_relationship_depth))

                linked[relationship] = subrelationship

            if len(linked) > 0:
                data['relationships'] = linked

        return data

# # Set default response
# set_response(
#     original=False,  # first_call=True,
#     custom_method=EndpointResource().default_response)
