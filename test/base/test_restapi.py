# -*- coding: utf-8 -*-

"""
Tests for http api base
(mostly authentication)
"""

from __future__ import absolute_import

import json
from .. import RestTestsBase
from commons.logs import get_logger

__author__ = "Paolo D'Onorio De Meo (p.donoriodemeo@cineca.it)"
logger = get_logger(__name__, True)


class BaseTests(RestTestsBase):

    """
    Unittests perpared for the core basic functionalities.

    - service is alive
    - login/logout
    - profile
    - tokens

    Note: security part should be checked even if it will not be enabled

    """

    def test_01_GET_status(self):
        """ Test that the flask server is running and reachable """

        # Check success
        endpoint = self._api_uri + '/status'
        logger.info("*** VERIFY if API is online")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)

        # Check failure
        logger.info("*** VERIFY if invalid endpoint gives Not Found")
        r = self.app.get(self._api_uri)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_NOTFOUND)

    def test_02_GET_specifications(self):
        """ Test that the flask server is running and reachable """

        # Check success
        endpoint = self._api_uri + '/spec'
        logger.info("*** VERIFY if API specifications are online")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)

    def test_03_GET_login(self):
        """ Check that you can login and receive back your token """

        endpoint = self._auth_uri + '/login'

        # Check success
        logger.info("*** VERIFY valid credentials")
        credentials = json.dumps(
            {'username': self._username, 'password': self._password})
        r = self.app.post(endpoint, data=credentials)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)
        content = self.get_content(r)

        # Note: self.auth_header does not work
        self.__class__.auth_header = {
            'Authorization': 'Bearer ' + content['token']}

        # Check failure
        logger.info("*** VERIFY invalid credentials")
        credentials = json.dumps({
            'username': self._username + 'X',
            'password': self._password + 'Y'
        })
        r = self.app.post(endpoint, data=credentials)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_04_GET_profile(self):
        """ Check if you can use your token for protected endpoints """

        endpoint = self._auth_uri + '/profile'

        # Check success
        logger.info("*** VERIFY valid token")
        r = self.app.get(endpoint, headers=self.__class__.auth_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)

        # Check failure
        logger.info("*** VERIFY invalid token")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_05_GET_logout(self):
        """ Check that you can logout with a valid token """

        endpoint = self._auth_uri + '/logout'

        # Check success
        logger.info("*** VERIFY valid token")
        r = self.app.get(endpoint, headers=self.__class__.auth_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_NORESPONSE)

        # Check failure
        logger.info("*** VERIFY invalid token")
        r = self.app.get(endpoint)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_UNAUTHORIZED)

    def test_06_GET_tokens(self):

        endpoint = self._auth_uri + '/login'

        # CREATING 3 TOKENS
        tokens = []
        num_tokens = 3
        credentials = json.dumps(
            {'username': self._username, 'password': self._password})

        for i in range(num_tokens):
            r = self.app.post(endpoint, data=credentials)
            content = self.get_content(r)
            token = content['token']
            tokens.append(token)

        endpoint = self._auth_uri + '/tokens'

        self.__class__.tokens_header = {
            'Authorization': 'Bearer ' + tokens[0]}

        # TEST GET ALL TOKENS (expected at least num_tokens)
        r = self.app.get(endpoint, headers=self.__class__.tokens_header)
        content = self.get_content(r)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)
        self.assertGreaterEqual(len(content), num_tokens)

        # save the second token to be used for further tests
        self.__class__.token_id = str(content.pop(1)["id"])

        # TEST GET SINGLE TOKEN
        r = self.app.get(endpoint + "/" + self.__class__.token_id,
                         headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)

        # TEST GET INVALID SINGLE TOKEN
        r = self.app.get(endpoint + "/0",
                         headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_NOTFOUND)

    def test_07_DELETE_tokens(self):

        endpoint = self._auth_uri + '/tokens'

        # TEST DELETE OF A SINGLE TOKEN
        r = self.app.delete(endpoint + "/" + self.__class__.token_id,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_NORESPONSE)

        # TEST AN ALREADY DELETED TOKEN
        r = self.app.delete(endpoint + "/" + self.__class__.token_id,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_NOTFOUND)

        # TEST INVALID DELETE OF A SINGLE TOKEN
        r = self.app.delete(endpoint + "/0",
                            headers=self.__class__.tokens_header)

        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_NOTFOUND)

        # TEST DELETE OF ALL TOKENS
        r = self.app.delete(endpoint,
                            headers=self.__class__.tokens_header)
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_NORESPONSE)

        # TEST TOKEN IS NOW INVALID
        r = self.app.get(endpoint,
                         headers=self.__class__.tokens_header)

        self.assertEqual(r.status_code, self._hcodes.HTTP_BAD_UNAUTHORIZED)
