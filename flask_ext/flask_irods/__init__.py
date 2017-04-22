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

"""
When connection errors occurs:
irods.exception.NetworkException:
    Could not connect to specified host and port:
        pippodata.repo.cineca.it:1247
"""


class IrodsPythonExt(BaseExtension):

    # def prepare_session(self, user=None):
    def pre_connection(self, **kwargs):

        user = kwargs.get('user')
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

        # if os.environ.get('X509_CERT_DIR') is None:
        if self.variables.get("x509_cert_dir") is None:
            os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')
        else:
            os.environ['X509_CERT_DIR'] = self.variables.get("x509_cert_dir")

        if os.path.isdir(cpath):
            os.environ['X509_USER_KEY'] = os.path.join(cpath, 'userkey.pem')
            os.environ['X509_USER_CERT'] = os.path.join(cpath, 'usercert.pem')
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
                    myproxy_host = "grid.hpc.cineca.it"

                    valid = Certificates.get_myproxy_certificate(
                        # TO FIX: X509_CERT_DIR should be enough
                        irods_env=irods_env,
                        irods_user=user,
                        myproxy_cert_name=cert_name,
                        irods_cert_pwd=cert_pwd,
                        proxy_cert_file=proxy_cert_file,
                        myproxy_host=myproxy_host
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

        client = IrodsPythonClient(obj)
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
