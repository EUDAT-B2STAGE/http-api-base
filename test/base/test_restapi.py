# -*- coding: utf-8 -*-

"""
Tests for http api base
(mostly authentication)
"""

from __future__ import absolute_import

import json
import unittest
import commons.htmlcodes as hcodes
from restapi.server import create_app
from restapi.confs.config import USER, PWD, \
    TEST_HOST, SERVER_PORT, API_URL, AUTH_URL

from commons import myself
from commons.logs import get_logger

__author__ = myself
logger = get_logger(__name__, True)

API_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, API_URL)
AUTH_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, AUTH_URL)


class TestRestAPI(unittest.TestCase):

    """
    HOW TO

    # initialization logic for the test suite declared in the test module
    # code that is executed before all tests in one test run
    @classmethod
    def setUpClass(cls):
        pass

    # clean up logic for the test suite declared in the test module
    # code that is executed after all tests in one test run
    @classmethod
    def tearDownClass(cls):
        pass

    # initialization logic
    # code that is executed before each test
    def setUp(self):
        pass

    # clean up logic
    # code that is executed after each test
    def tearDown(self):
        pass
    """

    def setUp(self):
        """
        Note: in this base tests,
        I also want to check if i can run multiple Flask applications.

        Thi is why i prefer setUp on setUpClass
        """
        logger.debug('### Setting up the Flask server ###')
        app = create_app(testing=True)
        self.app = app.test_client()

    def tearDown(self):
        logger.debug('### Tearing down the Flask server ###')
        del self.app

        # Tokens clean up
        logger.debug("Cleaned up invalid tokens")
        from restapi.resources.services.neo4j.graph import MyGraph
        MyGraph().clean_pending_tokens()

    def test_01_get_status(self):
        """ Test that the flask server is running and reachable """

        # Check success
        endpoint = API_URI + '/status'
        logger.info("*** VERIFY if API is online")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)

        # Check failure
        logger.info("*** VERIFY if invalid endpoint gives Not Found")
        r = self.app.get(API_URI)
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_NOTFOUND)

    def test_02_get_login(self):
        """ Check that you can login and receive back your token """

        endpoint = AUTH_URI + '/login'

        # Check success
        logger.info("*** VERIFY valid credentials")
        r = self.app.post(endpoint,
                          data=json.dumps({'username': USER, 'password': PWD}))
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)

        content = json.loads(r.data.decode('utf-8'))
        # Since unittests use class object and not instances
        # This is the only workaround to set a persistent variable
        # self.auth_header does not work
        self.__class__.auth_header = {
            'Authorization': 'Bearer ' + content['Response']['data']['token']}

        # Check failure
        logger.info("*** VERIFY invalid credentials")
        r = self.app.post(
            endpoint,
            data=json.dumps({'username': USER + 'x', 'password': PWD + 'y'}))
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_03_get_profile(self):
        """ Check if you can use your token for protected endpoints """

        endpoint = AUTH_URI + '/profile'

        # Check success
        logger.info("*** VERIFY valid token")
        r = self.app.get(endpoint, headers=self.__class__.auth_header)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)

        # Check failure
        logger.info("*** VERIFY invalid token")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_04_get_logout(self):
        """ Check that you can logout with a valid token """

        endpoint = AUTH_URI + '/logout'

        # Check success
        logger.info("*** VERIFY valid token")
        r = self.app.get(endpoint, headers=self.__class__.auth_header)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_NORESPONSE)

        # Check failure
        logger.info("*** VERIFY invalid token")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_05_get_tokens(self):

        endpoint = AUTH_URI + '/login'

        # CREATING 3 TOKENS
        tokens = []
        num_tokens = 3

        for i in range(num_tokens):
            r = self.app.post(endpoint, data=json.dumps({
                                                        'username': USER,
                                                        'password': PWD
                                                        }))
            content = json.loads(r.data.decode('utf-8'))
            token = content['Response']['data']['token']
            tokens.append(token)

        endpoint = AUTH_URI + '/tokens'

        self.__class__.tokens_header = {
            'Authorization': 'Bearer ' + tokens[0]}

        # TEST GET ALL TOKENS (expected at least num_tokens)
        r = self.app.get(endpoint, headers=self.__class__.tokens_header)
        content = json.loads(r.data.decode('utf-8'))
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)
        self.assertGreaterEqual(len(content['Response']['data']), num_tokens)

        # save the second token to be used for further tests
        data = content['Response']['data']
        self.__class__.token_id = str(data.pop(1)["id"])

        # TEST GET SINGLE TOKEN
        r = self.app.get(endpoint + "/" + self.__class__.token_id,
                         headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)

        # TEST GET INVALID SINGLE TOKEN
        r = self.app.get(endpoint + "/0",
                         headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_NOTFOUND)

    def test_06_delete_tokens(self):

        endpoint = AUTH_URI + '/tokens'

        # TEST DELETE OF A SINGLE TOKEN
        r = self.app.delete(endpoint + "/" + self.__class__.token_id,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_NORESPONSE)

        # TEST AN ALREADY DELETED TOKEN
        r = self.app.delete(endpoint + "/" + self.__class__.token_id,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, hcodes.HTTP_BAD_NOTFOUND)

        # TEST INVALID DELETE OF A SINGLE TOKEN
        r = self.app.delete(endpoint + "/0",
                            headers=self.__class__.tokens_header)

        self.assertEqual(r.status_code, hcodes.HTTP_BAD_NOTFOUND)

        # TEST DELETE OF ALL TOKENS
        r = self.app.delete(endpoint,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, hcodes.HTTP_OK_NORESPONSE)

        # TEST TOKEN IS NOW INVALID
        r = self.app.get(endpoint,
                         headers=self.__class__.tokens_header)

        self.assertEqual(r.status_code, hcodes.HTTP_BAD_UNAUTHORIZED)
