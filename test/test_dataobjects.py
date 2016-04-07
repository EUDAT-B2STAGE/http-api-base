# -*- coding: utf-8 -*-

"""
Test  dataobjects endpoints
"""

from restapi.server import create_app
import io

from nose.tools import assert_equals

__author__ = 'Roberto Mucci (r.mucci@cineca.it)'


class TestDataObjects(object):

    @classmethod
    def setup_class(self):
        "set up test fixtures"
        print('### Inside fixture ###')
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
        r = self.app.post('http://localhost:8080/api/dataobjects', data=dict(
        file=(io.BytesIO(b"this is a test"), 'test1.pdf'),))
        print(r.status_code)
        assert_equals(r.status_code, 200)
