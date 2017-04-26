# -*- coding: utf-8 -*-

""" iRODS file-system flask connector """

import os
import logging
from irods.session import iRODSSession
from rapydo.utils.certificates import Certificates
from flask_ext import BaseExtension, get_logger
from flask_ext.flask_irods.client import IrodsPythonClient

# Silence too much logging from irods
irodslogger = logging.getLogger('irods')
irodslogger.setLevel(logging.INFO)

log = get_logger(__name__)

# TO FIX: @mattia, make it an external variable
MYPROXY_HOST = "grid.hpc.cineca.it"

"""
When connection errors occurs:
irods.exception.NetworkException:
    Could not connect to specified host and port:
        pippodata.repo.cineca.it:1247
"""


class IrodsPythonExt(BaseExtension):

    def pre_connection(self, **kwargs):

        user = kwargs.get('user')
        proxy = kwargs.get('proxy', False)
        admin = kwargs.get('be_admin', False)

        if user is None:
            if not self.variables.get('external') and admin:
                # Note: 'user' is referring to the main user inside iCAT
                user = self.variables.get('default_admin_user')
            else:
                # There must be some way to fallback here
                user = self.variables.get('default_user')

        if user is None:
            raise AttributeError("No user is defined")
        else:
            self.user = user
            log.verbose("Irods user: %s" % self.user)

        # Identity with GSI

        # TO FIX: move this into certificates.py?
        cdir = Certificates._dir
        cpath = os.path.join(cdir, self.user)

        xcdir = self.variables.get("x509_cert_dir")
        if xcdir is None:
            os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')
        else:
            os.environ['X509_CERT_DIR'] = xcdir

        if os.path.isdir(cpath):
            if proxy:
                raise NotImplementedError("to do!")
                os.environ['X509_USER_PROXY'] = os.path.join('userproxy.crt')
            else:
                os.environ['X509_USER_KEY'] = \
                    os.path.join(cpath, 'userkey.pem')
                os.environ['X509_USER_CERT'] = \
                    os.path.join(cpath, 'usercert.pem')
        else:
            proxy_cert_file = cpath + '.pem'
            if not os.path.isfile(proxy_cert_file):
                # Proxy file does not exist
                valid = False
            else:
                valid, not_before, not_after = \
                    Certificates.check_certificate_validity(proxy_cert_file)
                if not valid:
                    log.warning(
                        "Invalid proxy certificate for %s. Validity: %s - %s"
                        % (user, not_before, not_after)
                    )

            # Proxy file does not exist or expired
            if not valid:
                log.warning("Creating a new proxy for %s" % user)
                try:

                    irods_env = os.environ
                    # cert_pwd = user_node.irods_cert
                    cert_name = kwargs.pop("proxy_cert_name")
                    cert_pwd = kwargs.pop("proxy_pass")

                    valid = Certificates.get_myproxy_certificate(
                        # TO FIX: X509_CERT_DIR should be enough
                        irods_env=irods_env,
                        irods_user=user,
                        myproxy_cert_name=cert_name,
                        irods_cert_pwd=cert_pwd,
                        proxy_cert_file=proxy_cert_file,
                        myproxy_host=MYPROXY_HOST
                    )

                    if valid:
                        log.info("Proxy refreshed for %s" % user)
                    else:
                        log.error("Got invalid proxy for user %s" % user)
                except Exception as e:
                    log.critical("Cannot refresh proxy for user %s" % user)
                    log.critical(e)

            ##################
            if valid:
                os.environ['X509_USER_KEY'] = proxy_cert_file
                os.environ['X509_USER_CERT'] = proxy_cert_file
            else:
                log.critical("Cannot find a valid certificate file")

    def custom_connection(self, **kwargs):

        # In case not set, recover from certificates we have
        if self.variables.get('dn') is None:
            # server host certificate
            self.variables['dn'] = Certificates.get_dn_from_cert(
                certdir='host', certfilename='hostcert')

        obj = iRODSSession(
            user=self.user,
            zone=self.variables.get('zone'),
            # password='thisismypassword', # authentication_scheme='password',
            authentication_scheme=self.variables.get('authscheme'),
            host=self.variables.get('host'),
            port=self.variables.get('port'),
            server_dn=self.variables.get('dn')
        )

        # Do a simple command to test this session
        u = obj.users.get(self.user)
        log.verbose("Testing iRODS session retrieving user %s" % u.name)

        client = IrodsPythonClient(rpc=obj, variables=self.variables)
        return client

    def custom_init(self, pinit=False, **kwargs):
        """ Note: we ignore args here """

        if pinit and not self.variables.get('external'):
            log.debug("waiting for internal certificates")
            # should actually connect with user and password
            # and verify if GSI is already registered with admin rodsminer
            import time
            time.sleep(5)

        # recover instance with the parent method
        return super().custom_init()
