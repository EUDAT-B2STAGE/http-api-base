# -*- coding: utf-8 -*-

""" Basic Resource """

from .. import htmlcodes as hcodes
# from confs.config import STACKTRACE
from ..jsonify import output_json  # , RESTError
from flask.ext.restful import request, Resource, reqparse, fields  # , abort
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
    # How to have a standard response
    resource_fields = {
        # html code embedded for semplicity
        'status': fields.Integer,
        # Hashtype, Vector, String, Int/Float, and so on
        'data_type': fields.String,
        # Count
        'elements': fields.Integer,
        # The real data
        'data': fields.Raw,
    }

    def __init__(self):
        super(ExtendedApiResource, self).__init__()
# NOTE: you can add as many representation as you want!
        self.representations = {
            # Be sure of handling JSON
            'application/json': output_json,
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

    def response(self,
                 data=None, elements=None,
                 fail=False, errors=None,
                 code=hcodes.HTTP_OK_BASIC):

# // TO FIX
# Note: 'fail' needs to be removed in the near future
        """
        Handle a standard response following
        criteria described in
        https://github.com/EUDAT-B2STAGE/http-api-base/issues/7
        """

        print("Received", data)
        # # Do not apply if the object has already been used
        # # as a 'standard response' from a parent call
        # if RESPONSE_CONTENT in data and RESPONSE_META in data:
        #     return data

        # check if 0 < code < 600

        #########################
        # Compute the elements

        # Case of failure
        if fail and code < http.HTTP_BAD_REQUEST:
            code = http.HTTP_BAD_REQUEST

        # Convert errors in a dictionary, always
        if errors is not None:
            if not isinstance(errors, list):
                if not isinstance(errors, dict):
                    errors = {'Generic error': errors}
                errors = [errors]
            errors = {'errors': errors}

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

        data_type = str(type(data))
        if elements is None:
            if isinstance(data, str):
                elements = 1
            else:
                elements = len(data)

        response = {
            RESPONSE_CONTENT: {
                'data': data,
                'errors': errors,
            },
            RESPONSE_META: {
                'elements': elements,
                'data_type': data_type,
                'status': int(code)
            }
        }

        # ## In case we want to handle the failure at this level
        # # I want to use the same marshal also if i say "fail"
        # if fail:
        #     code = hcodes.HTTP_BAD_REQUEST
        #     if STACKTRACE:
        #         # I could raise my exception if i need again stacktrace
        #         raise RESTError(obj, status_code=code)
        #     else:
        #         # Normal abort
        #         abort(code, **response)
        # ## But it's probably a better idea to do it inside the decorators

        return response, code
