# -*- coding: utf-8 -*-

import os
from rapydo.utils.meta import Meta
from rapydo.confs import PRODUCTION
from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class Authenticator(BaseExtension):

    _custom_auth = None

    def get_authentication_module(self, auth_service):
        meta = Meta()

        module_name = "%s.%s.%s" % ('services', 'authentication', auth_service)
        log.verbose("Loading auth extension: %s" % module_name)
        module = meta.get_module_from_string(module_name, prefix_package=True)

        return module

    def custom_connection(self):

        print("SHOULD BE CALLED ONLY ONCE??")
        # TO BE FIXED...

        # What service will hold authentication?
        auth_service = os.environ.get('AUTH_SERVICE')
        if auth_service is None:
            raise ValueError("You MUST specify a service for authentication")
        else:
            log.verbose("Auth service '%s'" % auth_service)

        auth_module = self.get_authentication_module(auth_service)
        custom_auth = auth_module.Authentication(self.variables.get('service'))

        # If oauth services are available, set them before every request
        from rapydo.services.oauth2clients import ExternalLogins as oauth2
        if oauth2._check_if_services_exist():
            ext_auth = oauth2(self.app.config['TESTING'])
            custom_auth.set_oauth2_services(ext_auth._available_services)

        if self.app.config['TESTING']:
            secret = 'IaMvERYsUPERsECRET'
        else:
            secret = str(
                custom_auth.import_secret(self.app.config['SECRET_KEY_FILE'])
            )

        # Install self.app secret for oauth2
        self.app.secret_key = secret + '_app'

        # Enabling also OAUTH library
        from rapydo.protocols.oauth import oauth
        oauth.init_app(self.app)

        self._custom_auth = custom_auth
        return self._custom_auth

    def custom_initialization(self, extras):

        obj = self._custom_auth
        # A little trick here:
        # We may pass around instances of services.
        # In particular an instance of a database to be used
        # as the backend service of authentication
        # The extra service is the injector, so I provided the method
        # 'internal_object' to recover the service instance
        obj._db = extras.get('extra_service').internal_object()
        obj.init_users_and_roles()
        log.warning("Initialized auth")

        ####################
        # TODO: check this piece of code
        if PRODUCTION and obj.check_if_user_defaults():
            raise AttributeError("PRODUCTION mode with default admin user?")


class AuthInjector(BaseInjector):

    def custom_configure(self):
        # note: no models
        auth = Authenticator(self.app, self._variables)
        return Authenticator, auth
