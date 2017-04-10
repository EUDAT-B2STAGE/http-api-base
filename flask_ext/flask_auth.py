# -*- coding: utf-8 -*-

# from rapydo.confs import PRODUCTION
from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class Authenticator(BaseExtension):

    def custom_connection(self, **kwargs):

        # # What service will hold authentication?
        auth_service = self.variables.get('service')
        auth_module = self.meta.get_authentication_module(auth_service)
        custom_auth = auth_module.Authentication()

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

        return custom_auth

    def custom_init(self, auth_backend=None):

        obj = super().custom_init()
        obj.db = auth_backend

        with self.app.app_context():
            obj.init_users_and_roles()
            log.info("Initialized auth")

        # ####################
        # # TODO: check this piece of code
        # if PRODUCTION and obj.check_if_user_defaults():
        #     raise AttributeError("PRODUCTION mode with default admin user?")


class AuthInjector(BaseInjector):
    pass
