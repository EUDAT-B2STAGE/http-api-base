# -*- coding: utf-8 -*-

"""
Test  dataobjects endpoints
"""

from __future__ import absolute_import

import unittest
import logging
import restapi.htmlcodes as hcodes
from restapi.server import create_app
from restapi import get_logger, myself
from confs.config import USER, PWD, \
    TEST_HOST, SERVER_PORT, API_URL, AUTH_URL

__author__ = myself
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

API_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, API_URL)
AUTH_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, AUTH_URL)


class TestRestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        logger.debug('### Setting up the Flask server ###')
        app = create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()

    @classmethod
    def tearDownClass(self):
        logger.debug('### Tearing down the Flask server ###')

    def test_01_get_status(self):
        """
        Test that the flask server is running and reachable
        """

        logger.info("Verify if API is online")
        r = self.app.get(API_URI + '/status')
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)

# https://github.com/kelsmj/flask-test-example/blob/master/tests/testusers.py

# Create a user

# Login

# Token

# Logout

# Delete user

    def test_03_get_login(self):
        """
        Test that the flask server is running and reachable
        """

        logger.info("Verify credentials")
        import json
        r = self.app.post(
            AUTH_URI + '/login',
            data=json.dumps({'username': USER, 'password': PWD}))
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)
