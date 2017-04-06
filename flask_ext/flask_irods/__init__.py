# -*- coding: utf-8 -*-

""" iRODS file-system flask connector """

import os
import logging
from irods.session import iRODSSession
from rapydo.utils.certificates import Certificates
from flask_ext import BaseInjector, BaseExtension, get_logger
from flask_ext.flask_irods.client import IrodsPythonClient

# Silence too much logging from irods
irodslogger = logging.getLogger('irods')
irodslogger.setLevel(logging.INFO)

log = get_logger(__name__)

"""
When connection errors occurs:
irods.exception.NetworkException:
    Could not connect to specified host and port:
        pippodata.repo.cineca.it:1247
"""


class IrodsPythonExt(BaseExtension):

    def prepare_session(self, user=None):
        if user is None:
            self.user = self.variables.get('default_admin_user')
            # Note: 'user' is referring to the main user inside iCAT
            # self.user = self.variables.get('user')
        else:
            self.user = user

        # identity GSI

        # TO FIX: move this into certificates.py?
        cdir = Certificates._dir
        cpath = os.path.join(cdir, self.user)
        os.environ['X509_USER_KEY'] = os.path.join(cpath, 'userkey.pem')
        os.environ['X509_USER_CERT'] = os.path.join(cpath, 'usercert.pem')

        # if os.environ.get('X509_CERT_DIR') is None:
        if self.variables.get("x509_cert_dir") is None:
            os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')
        else:
            os.environ['X509_CERT_DIR'] = self.variables.get("x509_cert_dir")

        # server host certificate
        self._hostdn = Certificates.get_dn_from_cert(
            user='host', certfilename='hostcert')

    def session(self):
        irods_session = iRODSSession(
            user=self.user,
            zone=self.variables.get('zone'),
            # password='thisismypassword', # authentication_scheme='password',
            authentication_scheme=self.variables.get('authscheme'),
            host=self.variables.get('host'),
            port=self.variables.get('port'),
            server_dn=self._hostdn,
        )
        return irods_session

    def custom_connection(self):
        # self.prepare_session()
        obj = self.session()

        # Do a simple command to test this session
        u = obj.users.get(self.user)
        log.verbose("Testing iRODS session retrieving user %s" % u.name)

        client = IrodsPythonClient(obj)
        return client

    def custom_initialization(self, obj=None):
        log.verbose("No initialization for now in irods?")
        pass


class RPCInjector(BaseInjector):

    def custom_configure(self):
        # note: no models
        rpc = IrodsPythonExt(self.app, self._variables)  # , self._models)
        # set session variables once
        rpc.prepare_session()

        return IrodsPythonExt, rpc
