# -*- coding: utf-8 -*-

"""

Handle the response 'algorithm'
(see EUDAT-B2STAGE/http-api-base#7)

force_response (base.py)    or              simple return
[ResponseElements()]        [obj / (content,status) / (content,status,headers)]
        |                                           |
        ---------------------------------------------
                            |
            Overriden Flask.make_response (server.py) - called internally
             |- x = ResponseMaker(rv) instance __init__
             |- x.generate_response()
                    |
                get_custom_or_default_response_method
                get_errors
                set_standard to output ({Response: OUT, Meta: ...})
                return tuple (data, status, headers)
                                        |
            Flask handle over to overridden Werkzeug Response
             |- force_type: jsonify
                    |
                   THE END

"""

import attr
from attr import (
    s as AttributedModel,
    ib as attribute,
)
from .jsonify import json
from flask import Response, jsonify
from werkzeug import exceptions as wsgi_exceptions
from werkzeug.wrappers import Response as werkzeug_response
from commons import htmlcodes as hcodes
from .resources.decorators import get_response, set_response
# from .resources.base import ExtendedApiResource
from commons.logs import get_logger

logger = get_logger(__name__)

# useful for pagination
CURRENTPAGE_KEY = 'currentpage'
DEFAULT_CURRENTPAGE = 1
PERPAGE_KEY = 'perpage'
DEFAULT_PERPAGE = 10

# response elements
RESPONSE_CONTENT = "Response"
RESPONSE_META = "Meta"


########################
# Flask custom response
########################

class InternalResponse(Response):
    """
    Note: basically the response cannot be modified anymore at this point
    """

    # def __init__(self, response, **kwargs):
    def __init__(self, *args, **kwargs):

        # print("TEST", args, kwargs)

        if 'mimetype' not in kwargs and 'contenttype' not in kwargs:
            # our default
            kwargs['mimetype'] = 'application/json'

            # if response.startswith('<?xml'):
            #     kwargs['mimetype'] = 'application/xml'

        self._latest_response = \
            super().__init__(*args, **kwargs)
        #    super().__init__(response, **kwargs)  # THIS WAS A HUGE BUG :/

    @classmethod
    def force_type(cls, rv, environ=None):
        """ Copy/paste from Miguel's tutorial """

        if isinstance(rv, dict):
            try:
                rv = jsonify(rv)
                logger.debug("Jsonified response")
            except:
                logger.error("Cannot jsonify rv")

        return super(InternalResponse, cls).force_type(rv, environ)


########################
# Elements for response
########################
@AttributedModel
class ResponseElements(object):
    defined_content = attribute()
    elements = attribute(default=None)
    code = attribute(default=None)
    errors = attribute(default=None)
    headers = attribute(default={})
    extra = attribute(default=None)


########################
# Flask response internal builder
########################
class ResponseMaker(object):

    def __init__(self, response):
        # logger.debug("Making a response")
        self._response = self.parse_elements(response)

    @staticmethod
    def is_internal_response(response):
        return isinstance(response, InternalResponse)

    @staticmethod
    def is_internal_exception(response):
        if isinstance(response, wsgi_exceptions.NotFound):
            return True
        return False

    def parse_elements(self, response):

        if self.is_internal_response(response):
            return response

        # Initialize the array of data
        elements = {}

        if isinstance(response, ResponseElements):
            elements = attr.asdict(response)
        else:
            for element in attr.fields(ResponseElements):
                elements[element.name] = element.default
            elements['defined_content'] = None

            # A Flask tuple. Possibilities:
            # obj / (content,status) / (content,status,headers)
            if isinstance(response, tuple):
                if len(tuple) > 0:
                    elements['defined_content'] = response[0]
                if len(tuple) > 1:
                    elements['code'] = response[1]
                if len(tuple) > 2:
                    elements['headers'] = response[2]
            # Anything that remains is just a content
            else:
                elements['defined_content'] = response

        return elements

    @staticmethod
    def default_response(content):
        """
        Our default for response content
        """
##Follow jsonapi.org?
        return content

    def already_converted(self):
        return self.is_internal_response(self._response)

    def generate_response(self):
        """
        Generating from our user/custom/internal response
        the data necessary for a Flask response (make_response() method):
        a tuple (content, status, headers)
        """

        if self.already_converted():
            return self._response

        # 1. Use response elements
        r = self._response

        # 2. Apply DEFAULT or CUSTOM manipulation
        # (strictly to the sole content)
        method = get_response()
        logger.debug("Apply response method: %s" % method)
        r['defined_content'] = method(r['defined_content'])

        # 3. Recover correct status and errors
        r['code'], r['errors'] = self.get_errors_and_status(
            r['defined_content'], r['code'], r['errors'])

        # 4. Encapsulate response and other things in a standard json obj:
        # {Response: DEFINED_CONTENT, Meta: HEADERS_AND_STATUS}
        final_content = self.standard_response_content(
            r['defined_content'], r['errors'], r['code'], r['elements'])

        if r['extra'] is not None:
            logger.warning("What to do with extra?\n%s" % r['extra'])

        # 5. Return what is necessary to build a standard flask response
        # from all that was gathered so far
        response = (final_content, r['code'], r['headers'])

        return response

    def get_errors_and_status(
            self, defined_content=None, code=None, errors=None):
        """
        Handle OUR standard response following criteria described in
        https://github.com/EUDAT-B2STAGE/http-api-base/issues/7
        """

        if code is None:
            # flask exception?
            if self.is_internal_exception(defined_content):
                exception = defined_content
                code = exception.code
                errors = exception.name
            else:
                code = hcodes.HTTP_OK_BASIC

        #########################
        # errors and conseguent status code range

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
        else:
            # warnings:
            # range 300 < 400
            pass

        return code, errors

    @staticmethod
    def standard_response_content(
            defined_content=None, errors=None, code=None, elements=None):
        """
        Try conversions and compute types and length
        """

        ###################
        # Handle original Flask wsgi_exceptions
        if ResponseMaker.is_internal_exception(defined_content):
            # Up to here the exception should be already parsed
            # for error and code in the previous step, so clean the content
            defined_content = None

        ###################
        # Our normal content
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

    @staticmethod
    def flask_response(data, status=hcodes.HTTP_OK_BASIC, headers=None):
        pass
#         """
#         Inspired by
#         http://blog.miguelgrinberg.com/
#             post/customizing-the-flask-response-class

# # THIS IS NOW DEPRECATED, DON'T USE IT!!
#         """

#         print("TEST_10: flask response inside base")
#         # print(data, status, headers)

#         #######################################
#         # Skip this method if the whole data
#         # is already a Flask Response

#         # Based on hierarchy: flask response extends werkezeug
#         # So I can be more flexible
#         if isinstance(data, werkzeug_response):
#             return data

#         # Handle normal response (not Flaskified)
#         if isinstance(data, tuple) and len(data) == 2:
#             print("NORMAL RESPONSE")
#             subdata, substatus = data
#             data = subdata
#             if isinstance(substatus, int):
#                 status = substatus

#         #######################################
#         # Create the Flask original response
#         # response = make_response((jsonify(data), status))
#         response = make_response((data, status))

#         #######################################
#         # # Handle headers if specified by the user
#         # response_headers = response.headers.keys()
#         # for header, header_content in headers.items():
#         #     # Only headers that are missing
#         #     if header not in response_headers:
#         #         response.headers[header] = header_content
# # UHM
#         response.headers.extend(headers or {})
#         # response = make_response((data, status, headers)) ?

#         #######################################
#         # Return the Flask Response
#         return response


########################
# Set default response
set_response(
    # Note: original here means the Flask simple response
    original=False,
    # first_call=True,
    custom_method=ResponseMaker.default_response)


########################
# Explode the normal response content?
def get_content_from_response(http_out):

    response = None

    # Read a real flask response
    if isinstance(http_out, werkzeug_response):
        try:
            response = json.loads(http_out.get_data().decode())
        except Exception as e:
            logger.critical("Failed to load response:\n%s" % e)
            raise ValueError(
                "Trying to recover informations" +
                " from a malformed response:\n%s" % http_out)
    # Or convert an half-way made response
    elif isinstance(http_out, ResponseElements):
        tmp = ResponseMaker(http_out).generate_response()
        response = tmp[0]

    # Check what we have so far
    # Should be {Response: DATA, Meta: RESPONSE_METADATA}
    if not isinstance(response, dict) or len(response) != 2:
        raise ValueError(
            "Trying to recover informations" +
            " from a malformed response:\n%s" % response)

    # Split
    content = response[RESPONSE_CONTENT]['data']
    err = response[RESPONSE_CONTENT]['errors']
    meta = response[RESPONSE_META]
    code = meta['status']

    return content, err, meta, code