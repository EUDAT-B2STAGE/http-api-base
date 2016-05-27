# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from ... import myself, lic, get_logger

import os
from ...oauth import oauth
from base64 import b64encode

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

B2ACCESS_DEV_URL = "https://unity.eudat-aai.fz-juelich.de:8443"


class ExternalServicesLogin(object):

    # _current = None

    # def __init__(self, service='b2access', testing=False):

    #     if self._current is None:
    #         method = getattr(self, service)
    #         method()

    def github(self):

        logger.debug("Oauth2 service github")

        self._current = oauth.remote_app(
            'github',
            consumer_key='',
            consumer_secret='',
            base_url='https://github.com/login/oauth',
            request_token_params={'scope': 'user'},
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize'
        )
        return self._current

    def b2access(self, testing=False):

        if testing:
            return None

        logger.debug("Oauth2 service b2access")

        # The B2ACCESS DEVELOPMENT
        self._current = oauth.remote_app(
            'b2access',
            consumer_key=os.environ.get('B2ACCESS_APPNAME', 'yourappusername'),
            consumer_secret=os.environ.get('B2ACCESS_APPKEY', 'yourapppw'),
            base_url=B2ACCESS_DEV_URL + '/oauth2/',
            # LOAD CREDENTIALS FROM DOCKER ENVIRONMENT
            request_token_params={'scope':
                                  'USER_PROFILE GENERATE_USER_CERTIFICATE'},
            request_token_url=None,
            access_token_method='POST',
            access_token_url=B2ACCESS_DEV_URL + '/oauth2/token',
            authorize_url=B2ACCESS_DEV_URL + '/oauth2-as/oauth2-authz'
        )
        return self._current


def decorate_http_request(remote):
    """
    Decorate the OAuth call to access token endpoint
    to inject the Authorization header
    """

    old_http_request = remote.http_request
    print("old http request", old_http_request)

    def new_http_request(uri, headers=None, data=None, method=None):
        response = None
        if not headers:
            headers = {}
        if not headers.get("Authorization"):
            client_id = remote.consumer_key
            client_secret = remote.consumer_secret
            userpass = b64encode(str.encode("%s:%s" %
                                 (client_id, client_secret))).decode("ascii")
            headers.update({'Authorization': 'Basic %s' % (userpass,)})
            # print(headers)
        try:
            response = old_http_request(
                uri, headers=headers, data=data, method=method)
        except Exception as e:
            logger.critical("Failed to authorize:\n%s" % str(e))
        return response
    remote.http_request = new_http_request
