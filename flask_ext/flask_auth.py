# -*- coding: utf-8 -*-

from flask_ext import BaseInjector, BaseExtension, get_logger

log = get_logger(__name__)


class Authenticator(BaseExtension):

    def package_connection(self):
        print("TEST PAOLO 1")
        return None


class AuthInjector(BaseInjector):

    def configure(self, binder):
        print("TEST PAOLO 2")
        return binder
