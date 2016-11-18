# -*- coding: utf-8 -*-

"""
Using x509 certificates
"""

from __future__ import absolute_import
import os
from .services.uuid import getUUID
from OpenSSL import crypto
from commons import htmlcodes as hcodes
from beeprint import pp as prettyprint

from .logs import get_logger

logger = get_logger(__name__)


class Certificates(object):

    def encode_csr(self, req):
        enc = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        data = {'certificate_request': enc}
        return data

    @staticmethod
    def generate_csr_and_key(user='TestUser'):
        """
        TestUser is the user proposed by the documentation,
        which will be ignored
        """
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.get_subject().CN = user
        req.set_pubkey(key)
        req.sign(key, "sha1")
        # print("CSR", key, req)
        return key, req

    def write_key_and_cert(self, key, cert):
        proxycertcontent = cert.decode()
        if proxycertcontent is None or proxycertcontent.strip() == '':
            return None
        tempfile = "/tmp/%s" % getUUID()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(tempfile, flags, 0o600), 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode())
            f.write(proxycertcontent)
        return tempfile

    def make_proxy_from_ca(self, ca):
        """
        Request for certificate and save it into a file
        """

        #######################
        # INSECURE SSL CONTEXT. IMPORTANT: to use only if not in production
        from flask import current_app
        if current_app.config['DEBUG']:
            # See more here:
            # http://stackoverflow.com/a/28052583/2114395
            import ssl
            ssl._create_default_https_context = \
                ssl._create_unverified_context
        else:
            raise NotImplementedError(
                "Please real signed certificates " +
                "to connect to B2ACCESS Certification Authority")

        #######################
        key, req = self.generate_csr_and_key()

        # Certificates should be trusted as i injected them
        # inside the docker image
        # #b2accessCA.http_request = http_request_no_verify_host

        #######################
        response = ca.post(
            'ca/o/delegateduser',
            data=self.encode_csr(req),
            headers={'Accept-Encoding': 'identity'})
        if response.status != hcodes.HTTP_OK_BASIC:
            # print("\nCertificate:"); prettyprint(response)
            logger.error("Proxy from CA failed with %s" % response.data)
            return None

        #######################
        # write proxy certificate to a random file name
        prettyprint(response)
        proxyfile = self.write_key_and_cert(key, response.data)
        logger.debug('Wrote certificate to %s' % proxyfile)

        return proxyfile
