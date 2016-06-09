# -*- coding: utf-8 -*-

"""
Using x509 certificates
"""

from __future__ import absolute_import

import logging
import os
from .services.uuid import getUUID
from OpenSSL import crypto

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Certificates(object):

    def __init__(self):
        super(Certificates, self).__init__()

    def generate_csr_and_key(self):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.get_subject().CN = 'TestUser'
        req.set_pubkey(key)
        req.sign(key, "sha1")
        return key, req

    def write_key_and_cert(self, key, cert):
        tempfile = "/tmp/%s" % getUUID()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(tempfile, flags, 0o600), 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
            f.write(cert)
        return tempfile

    def encode_csr(self, req):
        enc = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        data = {'certificate_request': enc}
        return data
