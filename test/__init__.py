# -*- coding: utf-8 -*-

"""
Test base
"""

from __future__ import absolute_import

import unittest
from restapi.server import create_app
from restapi.confs.config import \
    TEST_HOST, SERVER_PORT, API_URL, AUTH_URL
from restapi.response import get_content_from_response

from commons.logs import get_logger

__author__ = "Paolo D'Onorio De Meo (p.donoriodemeo@cineca.it)"
logger = get_logger(__name__, True)


class RestTestsBase(unittest.TestCase):

    _api_uri = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, API_URL)
    _auth_uri = 'http://%s:%s%s' % (TEST_HOST, SERVER_PORT, AUTH_URL)
    latest_response = None

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
        app = create_app(testing_mode=True)
        self.app = app.test_client()

    def tearDown(self):
        logger.debug('### Tearing down the Flask server ###')
        del self.app

        # Tokens clean up
## TO FIX:
# // this operation should be indipendent from the auth service
        # logger.debug("Cleaned up invalid tokens")
        # from restapi.resources.services.neo4j.graph import MyGraph
        # graph_instance = MyGraph()
        # if graph_instance:
        #     graph_instance.clean_pending_tokens()

        pass

    def get_content(self, response):
        content, err, meta, code = get_content_from_response(response)

        # Since unittests use class object and not instances
        # This is the only workaround to set a persistent variable:
        # abuse of the __class__ property

        self.__class__.latest_response = {
            "metadata": meta,
            "content": content,
            "errors": err,
            "status": code,
        }
        return content


#####################
class RestTestsAuthenticatedBase(RestTestsBase):

    def setUp(self):
        pass
