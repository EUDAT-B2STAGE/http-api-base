# -*- coding: utf-8 -*-

"""
Using x509 certificates
"""

from __future__ import absolute_import
import os
from .services.uuid import getUUID
from OpenSSL import crypto
from commons import htmlcodes as hcodes

from .logs import get_logger

logger = get_logger(__name__)


class Certificates(object):

    def encode_csr(self, req):
        enc = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        data = {'certificate_request': enc}
        return data

    @staticmethod
    def generate_csr_and_key(user='TestUser'):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.get_subject().CN = user
        req.set_pubkey(key)
        req.sign(key, "sha1")
        # print("CSR", key, req)
        return key, req

    def write_key_and_cert(self, key, cert):
        tempfile = "/tmp/%s" % getUUID()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(tempfile, flags, 0o600), 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode())
            f.write(cert.decode())
        return tempfile

    def make_proxy_from_ca(self, ca):
        """
        Request for certificate and save it into a file
        """

        key, req = self.generate_csr_and_key()

        # Certificates should be trusted as i injected them
        # inside the docker image
        # #b2accessCA.http_request = http_request_no_verify_host

        response = ca.post('ca/o/delegateduser', data=self.encode_csr(req),
                           headers={'Accept-Encoding': 'identity'})
        if response.status != hcodes.HTTP_OK_BASIC:
            # from beeprint import pp as prettyprint
            # prettyprint(response)
            logger.error("Proxy from CA failed with %s" % response.data)
            return None

        # write proxy certificate to a random file name
        proxyfile = self.write_key_and_cert(key, response.data)
        logger.debug('Wrote certificate to %s' % proxyfile)

        return proxyfile
