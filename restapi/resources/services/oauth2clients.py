# -*- coding: utf-8 -*-

"""
SECURITY ENDPOINTS CHECK
Add auth checks called /checklogged and /testadmin
"""

from __future__ import division, absolute_import
from ... import myself, lic, get_logger

import os
from ...oauth import oauth
from commons.meta import Meta
from base64 import b64encode

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

B2ACCESS_DEV_BASEURL = "https://unity.eudat-aai.fz-juelich.de"
B2ACCESS_DEV_URL = B2ACCESS_DEV_BASEURL + ":8443"
B2ACCESS_DEV_CA_URL = B2ACCESS_DEV_BASEURL + ":8445"


class ExternalServicesLogin(object):

    _available_services = {}

    def __init__(self, testing=False):

## // TO FIX?
        if testing:
            return None

        # For each defined internal service
        for key, func in Meta().get_methods_inside_instance(self).items():
            # Check if credentials are enabled inside docker env
            var1 = key.upper() + '_APPNAME'
            var2 = key.upper() + '_APPKEY'

            if var1 not in os.environ or var2 not in os.environ:
                logger.debug("Skipping Oauth2 service %s" % key)
                continue

            # Call the service and save it
            try:
                obj = func()

                # Make sure it's always a dictionary of objects
                if not isinstance(obj, dict):
                    obj = {key: obj}

                for name, oauth2 in obj.items():
                    self._available_services[name] = oauth2
                    logger.info("Created Oauth2 service %s" % name)
            except Exception as e:
                logger.critical(
                    "Could not request oauth2 service %s:\n%s" %
                    (key, str(e)))

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

        # print("TEST *%s*" % os.environ.get('B2ACCESS_APPKEY'))
        b2access_oauth = oauth.remote_app(
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

        b2accessCA = oauth.remote_app(
            'b2accessCA',
            consumer_key=os.environ.get('B2ACCESS_APPNAME', 'yourappusername'),
            consumer_secret=os.environ.get('B2ACCESS_APPKEY', 'yourapppw'),
            base_url=B2ACCESS_DEV_CA_URL,
            request_token_params={'scope':
                                  'USER_PROFILE GENERATE_USER_CERTIFICATE'},
            request_token_url=None,
            access_token_method='POST',
            access_token_url=B2ACCESS_DEV_URL + '/oauth2/token',
            authorize_url=B2ACCESS_DEV_URL + '/oauth2-as/oauth2-authz'
        )

        @b2access_oauth.tokengetter
        @b2accessCA.tokengetter
        def get_b2access_oauth_token():
            from flask import session
            return session.get('b2access_token')

        return {'b2access': b2access_oauth, 'b2accessCA': b2accessCA}


def decorate_http_request(remote):
    """
    Necessary for B2ACCESS oauth2 servers.

    Decorate the OAuth call
    to access token endpoint
    to inject the Authorization header.

    Original source (for Python2) by @akrause2014:
    https://github.com/akrause2014
        /eudat/blob/master/oauth2-client/b2access_client.py
    """

    old_http_request = remote.http_request
    # print("old http request", old_http_request)

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
        response = old_http_request(
            uri, headers=headers, data=data, method=method)
## // TO FIX: may we handle failed B2ACCESS response here?
        return response

    remote.http_request = new_http_request
