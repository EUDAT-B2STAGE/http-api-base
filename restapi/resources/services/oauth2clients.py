# -*- coding: utf-8 -*-

"""
Take care of authenticatin with External Service with Oauth2 protocol.

Testend against GitHub, then worked off B2ACCESS (EUDAT oauth service)
"""

from __future__ import absolute_import

import os
from ...oauth import oauth
from commons.meta import Meta
from base64 import b64encode
from ...confs.config import PRODUCTION, DEBUG as ENVVAR_DEBUG
from ... import myself, lic
from commons.logs import get_logger, pretty_print

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

B2ACCESS_DEV_BASEURL = "https://unity.eudat-aai.fz-juelich.de"
B2ACCESS_DEV_URL = B2ACCESS_DEV_BASEURL + ":8443"
B2ACCESS_DEV_CA_URL = B2ACCESS_DEV_BASEURL + ":8445"

B2ACCESS_PROD_BASEURL = "https://b2access.eudat.eu"
B2ACCESS_PROD_URL = B2ACCESS_PROD_BASEURL + ":8443"
B2ACCESS_PROD_CA_URL = B2ACCESS_PROD_BASEURL + ":8445"


class ExternalServicesLogin(object):

    _available_services = {}

    def __init__(self, testing=False):

###################
## // TO FIX?
# provide some tests for oauth2 calls?
        if testing:
            return None
###################

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
                    "Could not request oauth2 service %s:\n%s" % (key, e))

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

        # LOAD CREDENTIALS FROM DOCKER ENVIRONMENT
        key = os.environ.get('B2ACCESS_APPNAME', 'yourappusername')
        secret = os.environ.get('B2ACCESS_APPKEY', 'yourapppw')

        # SET OTHER URLS
        token_url = B2ACCESS_DEV_URL + '/oauth2/token'
        authorize_url = B2ACCESS_DEV_URL + '/oauth2-as/oauth2-authz'

        if PRODUCTION:
            if ENVVAR_DEBUG is None or not ENVVAR_DEBUG:
                token_url = B2ACCESS_PROD_URL + '/oauth2/token'
                authorize_url = B2ACCESS_PROD_URL + '/oauth2-as/oauth2-authz'
            else:
                logger.warning("Switching to b2access dev in production")

        # COMMON ARGUMENTS
        arguments = {
            'consumer_key': key,
            'consumer_secret': secret,
            'access_token_url': token_url,
            'authorize_url': authorize_url,
            'request_token_params':
                {'scope': ['USER_PROFILE', 'GENERATE_USER_CERTIFICATE']},
            'request_token_url': None,
            'access_token_method': 'POST'
        }

        #####################
        # B2ACCESS
        arguments['base_url'] = B2ACCESS_DEV_URL + '/oauth2/'
        if PRODUCTION:
            if ENVVAR_DEBUG is None or not ENVVAR_DEBUG:
                arguments['base_url'] = B2ACCESS_PROD_URL + '/oauth2/'
        # pretty_print(arguments)
        b2access_oauth = oauth.remote_app('b2access', **arguments)

        #####################
        # B2ACCESS CERTIFICATION AUTHORITY
        arguments['base_url'] = B2ACCESS_DEV_CA_URL
        if PRODUCTION:
            if ENVVAR_DEBUG is None or not ENVVAR_DEBUG:
                arguments['base_url'] = B2ACCESS_PROD_CA_URL
        # pretty_print(arguments)
        b2accessCA = oauth.remote_app('b2accessCA', **arguments)

        #####################
        # Decorated session save of the token
        @b2access_oauth.tokengetter
        @b2accessCA.tokengetter
        def get_b2access_oauth_token():
            from flask import session
            return session.get('b2access_token')

## // TO CHECK:
    ## could have used nametuple or attrs?
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
