import unittest
import random
import json
import string
import logging

from commons.logs import get_logger
from restapi.confs.config import TEST_HOST, SERVER_PORT, API_URL, AUTH_URL
import commons.htmlcodes as hcodes

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

API_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, API_URL)
AUTH_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, AUTH_URL)

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'

OK = hcodes.HTTP_OK_BASIC                           # 200
NO_CONTENT = hcodes.HTTP_OK_NORESPONSE              # 204
BAD_REQUEST = hcodes.HTTP_BAD_REQUEST               # 400
UNAUTHORIZED = hcodes.HTTP_BAD_UNAUTHORIZED         # 401
FORBIDDEN = hcodes.HTTP_BAD_FORBIDDEN               # 403
NOTFOUND = hcodes.HTTP_BAD_NOTFOUND                 # 404
NOT_ALLOWED = hcodes.HTTP_BAD_METHOD_NOT_ALLOWED    # 405
CONFLICT = hcodes.HTTP_BAD_CONFLICT                 # 409

NOT_ALLOWED_ERROR = {
    'message': 'The method is not allowed for the requested URL.'
}


class ParsedResponse(object):
    pass


class TestUtilities(unittest.TestCase):

    def save(self, variable, value, read_only=False):

        if hasattr(self.__class__, variable):
            data = getattr(self.__class__, variable)
            if "read_only" in data and data["read_only"]:
                self.assertFalse(
                    "Cannot overwrite a read_only variable [%s]" % variable
                )

        data = {'value': value, 'read_only': read_only}
        setattr(self.__class__, variable, data)

    def get(self, variable):
        if not hasattr(self.__class__, variable):
            return None

        data = getattr(self.__class__, variable)
        if "value" in data:
            return data["value"]
        return None

    def do_login(self, USER, PWD):

        r = self.app.post(AUTH_URI + '/login',
                          data=json.dumps({
                                          'username': USER,
                                          'password': PWD
                                          }))
        self.assertEqual(r.status_code, OK)

        content = json.loads(r.data.decode('utf-8'))

        token = content['Response']['data']['token']
        return {'Authorization': 'Bearer ' + token}, token

    def destroyToken(self, token, headers):
        r = self.app.get(AUTH_URI + '/tokens', headers=headers)
        self.assertEqual(r.status_code, OK)

        content = json.loads(r.data.decode('utf-8'))
        self.assertEqual(r.status_code, OK)

        for data in content['Response']['data']:
            if data["token"] == token:
                id = data["id"]
                uri = '%s/tokensadminonly/%s' % (AUTH_URI, id)
                r = self.app.delete(uri, headers=headers)
                self.assertEqual(r.status_code, NO_CONTENT)
                break

    def get_profile(self, headers):
        r = self.app.get(AUTH_URI + '/profile', headers=headers)
        content = json.loads(r.data.decode('utf-8'))
        return content['Response']['data']

    def getPartialData(self, schema, data):
        partialData = data.copy()
        for d in schema:
            if not d['required']:
                continue

            key = d["key"]

            del partialData[key]
            return partialData
        return None

    def randomString(self, len=16, prefix="TEST:"):
        rand = random.SystemRandom()
        charset = string.ascii_uppercase + string.digits

        random_string = prefix
        for _ in range(len):
            random_string += rand.choice(charset)

        return random_string

    def buildData(self, schema):
        data = {}
        for d in schema:

            key = d["key"]
            type = d["type"]
            value = None

            if type == "select":
                if len(d["options"]) > 0:
                    value = d["options"].pop(0)["value"]
                else:
                    value = ""
            elif type == "int":
                value = random.randrange(0, 1000, 1)
            else:
                value = self.randomString()

            data[key] = value

        return data

    def parseResponse(self, response, inner=False):

        # OLD RESPONSE, NOT STANDARD-JSON
        if not inner and isinstance(response, dict):
            return response

        if response is None:
            return None

        data = []

        self.assertIsInstance(response, list)

        for element in response:
            self.assertIsInstance(element, dict)
            self.assertIn("id", element)
            self.assertIn("type", element)
            # self.assertIn("links", element)
            self.assertIn("attributes", element)
            # self.assertIn("relationships", element)

            newelement = ParsedResponse()
            setattr(newelement, "_id", element["id"])
            setattr(newelement, "_type", element["type"])
            if "links" in element:
                setattr(newelement, "_links", element["links"])

            setattr(newelement, "attributes", ParsedResponse())

            for key in element["attributes"]:
                setattr(newelement.attributes, key, element["attributes"][key])

            if "relationships" in element:
                for relationship in element["relationships"]:
                    setattr(newelement, "_" + relationship,
                            self.parseResponse(
                                element["relationships"][relationship],
                                inner=True
                            ))

            data.append(newelement)

        return data

    def checkResponse(self, response, fields, relationships):
        """
        Verify that the response contains the given fields and relationships
        """

        for f in fields:
            # How to verify the existence of a property?
            # assertTrue will hide the name of the missing property
            # I can verify my self and then use an always-false assert
            if not hasattr(response[0].attributes, f):
                self.assertIn(f, [])

        for r in relationships:
            if not hasattr(response[0], "_" + r):
                self.assertIn(r, [])

    def _test_endpoint(self, endpoint, headers=None,
                       private_get=None,
                       private_post=None,
                       private_put=None,
                       private_delete=None):

        # # # TEST GET # # #
        r = self.app.get(API_URI + '/' + endpoint)
        if private_get is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_get:
            self.assertEqual(r.status_code, OK)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.get(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, OK)

        # # # TEST POST # # #
        r = self.app.post(API_URI + '/' + endpoint)
        if private_post is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_post:
            self.assertEqual(r.status_code, OK)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.post(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, OK)

        # # # TEST PUT # # #
        r = self.app.put(API_URI + '/' + endpoint)
        if private_put is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_put:
            self.assertEqual(r.status_code, BAD_REQUEST)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.put(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, BAD_REQUEST)

        # # # TEST DELETE # # #
        r = self.app.delete(API_URI + '/' + endpoint)
        if private_delete is None:
            self.assertEqual(r.status_code, NOT_ALLOWED)
        elif not private_delete:
            self.assertEqual(r.status_code, BAD_REQUEST)
        else:
            self.assertEqual(r.status_code, UNAUTHORIZED)

            r = self.app.delete(API_URI + '/' + endpoint, headers=headers)
            self.assertEqual(r.status_code, BAD_REQUEST)

    # headers should be optional, if auth is not required
    def _test_method(self, method, endpoint, headers,
                     status, parse_response=False,
                     data=None, error={}):

        if data is not None:
            data = json.dumps(data)

        URI = API_URI + '/' + endpoint

        if method == GET:
            r = self.app.get(URI, headers=headers)
        elif method == POST:
            r = self.app.post(URI, data=data, headers=headers)
        elif method == PUT:
            r = self.app.put(URI, data=data, headers=headers)
        elif method == DELETE:
            r = self.app.delete(URI, data=data, headers=headers)

        self.assertEqual(r.status_code, status)

        content = json.loads(r.data.decode('utf-8'))

        # In this case the response is returned by Flask
        if status == NOT_ALLOWED:
            self.assertEqual(content, NOT_ALLOWED_ERROR)
            return content

        if error is not None:
            errors = content['Response']['errors']
            if errors is not None:
                self.assertEqual(errors[0], error)

        if parse_response:
            return self.parseResponse(content['Response']['data'])
        return content['Response']['data']

    def _test_get(self, endpoint, headers,
                  status, parse_response=True,
                  error={}):

        return self._test_method(
            GET, endpoint, headers, status,
            parse_response=parse_response, error=error
        )

    def _test_create(self, endpoint, headers, data, status, error={}):

        return self._test_method(
            POST, endpoint, headers, status,
            data=data, error=error
        )

    # headers should be optional, if auth is not required
    def _test_update(self, endpoint, headers, data, status, error={}):

        return self._test_method(
            PUT, endpoint, headers, status,
            data=data, error=error
        )

    # headers should be optional, if auth is not required
    def _test_delete(self, endpoint, headers, status, error={}, data={}):

        return self._test_method(
            DELETE, endpoint, headers, status,
            data=data, error=error
        )
