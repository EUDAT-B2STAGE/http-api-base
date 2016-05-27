# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from ... import myself, lic, get_logger

import os
from ...oauth import oauth
from ...meta import Meta
from base64 import b64encode

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

B2ACCESS_DEV_URL = "https://unity.eudat-aai.fz-juelich.de:8443"


class ExternalServicesLogin(object):

    _available_services = {}

    def __init__(self, testing=False):

        if testing:
            return None

        # For each defined internal service
        for key, func in Meta().get_methods_inside_instance(self).items():
            # Check if credentials are enabled inside docker env
            var1 = key.upper() + '_APPNAME'
            var2 = key.upper() + '_APPKEY'
            if var1 in os.environ and var2 in os.environ:
                # Call the service and save it
                try:
                    self._available_services[key] = func()
                    logger.info("Created Oauth2 service %s" % key)
                except Exception as e:
                    logger.critical(
                        "Could not request oauth2 service %s:\n%s" %
                        (key, str(e)))
            else:
                logger.debug("Skipping Oauth2 service %s" % key)
            # print(key, func)

    def github(self):
        """ This APIs are very useful for testing purpose """

        return oauth.remote_app(
            'github',
            consumer_key=os.environ.get('GITHUB_APPNAME', 'yourappusername'),
            consumer_secret=os.environ.get('GITHUB_APPKEY', 'yourapppw'),
            base_url='https://github.com/login/oauth',
            request_token_params={'scope': 'user'},
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize'
        )

    def b2access(self, testing=False):

        return oauth.remote_app(
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


def decorate_http_request(remote):
    """
    Necessary for B2ACCESS oauth2 servers.

    Decorate the OAuth call
    to access token endpoint
    to inject the Authorization header.

    Original source (for Python2) by Amy:
    https://github.com/akrause2014
        /eudat/blob/master/oauth2-client/b2access_client.py
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
        try:
            response = old_http_request(
                uri, headers=headers, data=data, method=method)
        except Exception as e:
            logger.critical("Failed to authorize:\n%s" % str(e))
        return response
    remote.http_request = new_http_request
