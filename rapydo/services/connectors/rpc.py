# -*- coding: utf-8 -*-

import os
import logging
from irods.session import iRODSSession
from rapydo.utils.certificates import Certificates
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

corslogger = logging.getLogger('irods')
corslogger.setLevel(logging.INFO)


class MyFarm(object):
    """
        Testing RPC
    """

    def __init__(self, user='guest'):

        # user = 'irods'
        # user = 'rodsminer'

        # Move this into certificates.py?
        cdir = Certificates._dir
        cpath = os.path.join(cdir, user)

        os.environ['X509_USER_KEY'] = os.path.join(cpath, 'userkey.pem')
        os.environ['X509_USER_CERT'] = os.path.join(cpath, 'usercert.pem')
        os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')

        self._hostdn = Certificates.get_dn_from_cert(
            user='host', certfilename='hostcert')

        sess = iRODSSession(
            host='rodserver', port=1247, zone='tempZone',
            authentication_scheme='GSI', server_dn=self._hostdn,
            # user=user, password='thisismypassword',
            # authentication_scheme='password',
            user=user,
        )

        home = "/tempZone/home/" + user
        coll = sess.collections.get(home)
        print("Session", sess, coll)

        for col in coll.subcollections:
            print("COLL", col)

        exit(1)
