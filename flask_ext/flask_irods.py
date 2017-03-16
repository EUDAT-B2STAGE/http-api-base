# -*- coding: utf-8 -*-

""" iRODS file-system flask connector """

import os
import time
import logging
from irods.session import iRODSSession
from flask import _app_ctx_stack as stack
from flask_ext import get_logger, BaseInjector
from rapydo.utils.certificates import Certificates

# Silence too much logging from irods
irodslogger = logging.getLogger('irods')
irodslogger.setLevel(logging.INFO)

log = get_logger(__name__)


class IrodsPythonClient(object):

    def __init__(self, app=None, variables={}, models=[]):

        self.app = app
        self.variables = variables

        if app is not None:
            self.init_app(app)

        log.very_verbose("Vars: %s" % variables)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

    def connect(self, user=None):
        # print("variables:", self.variables)
        if user is None:
            # Note: 'user' is referring to the main user inside iCAT
            # self.user = self.variables.get('user')
            self.user = self.variables.get('default_admin_user')
        else:
            self.user = user

        ######################
        # zone = self.variables['zone']
        # if user is None:
        #     user = self.variables.get('user')
        # else:
        #     # build new home
        #     self.variables['home'] = '/%s/home/%s' % (zone, user)
        # home = self.variables.get('home')

        ######################
        # identity GSI

        # TO FIX: move this into certificates.py?
        cdir = Certificates._dir
        cpath = os.path.join(cdir, self.user)
        os.environ['X509_USER_KEY'] = os.path.join(cpath, 'userkey.pem')
        os.environ['X509_USER_CERT'] = os.path.join(cpath, 'usercert.pem')
        if os.environ.get('X509_CERT_DIR') is None:
            os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')

        # server host certificate
        self._hostdn = Certificates.get_dn_from_cert(
            user='host', certfilename='hostcert')

        ######################
        self.retry()
        log.info("Connected! %s" % self.rpc)

        return self.rpc

    def session(self):
        self.rpc = iRODSSession(
            user=self.user,
            zone=self.variables.get('zone'),
            # password='thisismypassword', # authentication_scheme='password',
            authentication_scheme=self.variables.get('authscheme'),
            host=self.variables.get('host'),
            port=self.variables.get('port'),
            server_dn=self._hostdn,
        )

    def retry(self, retry_interval=5, max_retries=-1):
        retry_count = 0
        while max_retries != 0 or retry_count < max_retries:
            retry_count += 1
            if retry_count > 1:
                log.verbose("testing again")
            if self.test_connection():
                break
            else:
                log.info("Service not available")
                time.sleep(retry_interval)

    def package_connection(self):
        self.session()
        # Do a simple query to test this session
        from irods.models import DataObject
        self.rpc.query(DataObject.owner_name).all()

    def test_connection(self, retry_interval=5, max_retries=0):
        try:
            self.package_connection()
            return True
        # except:
        except Exception as e:
            raise e
            print("Error", e)
            return False

    def teardown(self, exception):
        ctx = stack.top
        if hasattr(ctx, 'rpc'):
            # neo does not have an 'open' connection that needs closing
            # ctx.rpc.close()
            ctx.rpc = None

    @property
    def connection(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'rpc'):
                ctx.rpc = self.connect()
            return ctx.rpc


class RPCInjector(BaseInjector):

    def configure(self, binder):
        rpc = IrodsPythonClient(self.app, self._variables, self._models)
        # test connection the first time
        rpc.connect()
        binder.bind(IrodsPythonClient, to=rpc, scope=self.singleton)
        return binder
