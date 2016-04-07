# -*- coding: utf-8 -*-

"""
Test  dataobjects endpoints
"""

import io
from restapi.server import create_app
from nose.tools import assert_equals

__author__ = 'Roberto Mucci (r.mucci@cineca.it)'


class TestDataObjects(object):

    @classmethod
    def setup_class(self):
        "set up test fixtures"
        print('### Inside fixture: setting up flask server ###')
        app = create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()

    @classmethod
    def teardown_class(self):
        "tear down test fixtures"

    def test_get_verify(self):
        """ Test that the flask server is running and reachable"""
        r = self.app.get('http://localhost:8080/api/verify')
        print(r.status_code)
        assert_equals(r.status_code, 200)

    def test_post_dataobjects(self):
        """ Test file upload """
        # I need to understand who to reapeat the upload test, since
        # overwrite is not allowed
        r = self.app.post('http://localhost:8080/api/dataobjects', data=dict(
                           file=(io.BytesIO(b"this is a test"), 'test.pdf')))
        print(r.status_code)
        assert_equals(r.status_code, 200)
