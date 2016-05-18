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
from confs.config import TEST_HOST, SERVER_PORT, ALL_API_URL

__author__ = myself
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

API_URI = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, ALL_API_URL)


class TestDataObjects(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        logger.debug('### Setting up the Flask server ###')
        app = create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()

    @classmethod
    def tearDownClass(self):
        logger.debug('### Tearing down the Flask server ###')

    def test_01_get_verify(self):
        """
        Test that the flask server is running and reachable
        """

        logger.info("Verify if API is online")
        r = self.app.get(API_URI + '/verify')
        self.assertEqual(r.status_code, hcodes.HTTP_OK_BASIC)
