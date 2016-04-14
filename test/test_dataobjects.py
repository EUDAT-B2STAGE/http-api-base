# -*- coding: utf-8 -*-

"""
Test  dataobjects endpoints
"""

import io
import os
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

    def test_01_get_verify(self):
        """ Test that the flask server is running and reachable"""
        r = self.app.get('http://localhost:8080/api/verify')
        assert_equals(r.status_code, 200)

    def test_02_post_dataobjects(self):
        """ Test file upload: POST"""
        # I need to understand who to reapeat the upload test, since
        # overwrite is not allowed
        r = self.app.post('http://localhost:8080/api/dataobjects', data=dict(
                         file=(io.BytesIO(b"this is a test"),
                          'test.pdf')))
        assert_equals(r.status_code, 200)

    def test_03_post_large_dataobjects(self):
        """ Test large file upload """
        path = os.path.join('/home/irods', 'img.JPG')
        with open(path, "wb") as f:
            f.seek(100000000)  # 100MB file
            f.write(b"\0")
        r = self.app.post('http://localhost:8080/api/dataobjects', data=dict(
                         file=(open(path, 'rb'), 'img.JPG')))

#        print(r.status_code)
        os.remove(path)
        assert_equals(r.status_code, 200)

    def test_04_get_dataobjects(self):
        """ Test file download: GET """
        deleteURI = os.path.join('http://localhost:8080/api/dataobjects',
                                 'test.pdf')
        r = self.app.get(deleteURI, data=dict(collection=('/home/guest')))
#        print(r.data)
        assert_equals(r.status_code, 200)
        assert_equals(r.data, b'this is a test')

    def test_05_delete_dataobjects(self):
        """ Test file delete: DELETE """
        deleteURI = os.path.join('http://localhost:8080/api/dataobjects',
                                 'test.pdf')
        r = self.app.delete(deleteURI, data=dict(collection=('/home/guest')))
        assert_equals(r.status_code, 200)

        deleteURI = os.path.join('http://localhost:8080/api/dataobjects',
                                 'img.JPG')
        r = self.app.delete(deleteURI, data=dict(collection=('/home/guest')))
        assert_equals(r.status_code, 200)
