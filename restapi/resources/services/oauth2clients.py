# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from .. import myself, lic, get_logger
from ..oauth import oauth
from base64 import b64encode

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)


class ExternalServicesLogin(object):

    @staticmethod
    def github():
        return oauth.remote_app(
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

    @staticmethod
    def b2access():

        B2ACCESS_DEV_URL = "https://unity.eudat-aai.fz-juelich.de:8443"
        # The B2ACCESS DEVELOPMENT
        return oauth.remote_app(
            'b2access',
            consumer_key='yourappusername',
            consumer_secret='yourapppassword',
            base_url=B2ACCESS_DEV_URL + '/oauth2/',
            request_token_params={'scope':
                                  'USER_PROFILE GENERATE_USER_CERTIFICATE'},
            request_token_url=None,
            access_token_method='POST',
            access_token_url=B2ACCESS_DEV_URL + '/oauth2/token',
            authorize_url=B2ACCESS_DEV_URL + '/oauth2-as/oauth2-authz'
        )


def decorate_http_request(remote):
    """
    Decorate the OAuth call to access token endpoint
    to inject the Authorization header
    """

    old_http_request = remote.http_request

    def new_http_request(uri, headers=None, data=None, method=None):
        if not headers:
            headers = {}
        if not headers.get("Authorization"):
            client_id = remote.consumer_key
            client_secret = remote.consumer_secret
            userpass = b64encode(str.encode("%s:%s" %
                                 (client_id, client_secret))).decode("ascii")
            headers.update({'Authorization': 'Basic %s' % (userpass,)})
            # print(headers)
        return old_http_request(uri, headers=headers, data=data, method=method)
    remote.http_request = new_http_request
