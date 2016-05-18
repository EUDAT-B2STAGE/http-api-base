# -*- coding: utf-8 -*-

"""
Test  dataobjects endpoints
"""

from __future__ import absolute_import

import io
import os
import json
import unittest
from restapi.server import create_app

from restapi import get_logger

# LOGGER?

# COSTANTS?


__author__ = 'Roberto Mucci (r.mucci@cineca.it)'


class TestDataObjects(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        "set up test fixtures"
        print('### Setting up flask server ###')
        app = create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()

    @classmethod
    def tearDownClass(self):
        "tear down test fixtures"
        print('### Tearing down the flask server ###')

    def test_00_something(self):
        """ Test that the flask server is running and reachable"""

        r = self.app.get('http://localhost:8081/api/verify')
        self.assertEqual(r.status_code, 200)
