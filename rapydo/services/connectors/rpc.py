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

    def __init__(self, user=None):

        ######################
        # user, zone, home

        # user = 'irods'
        # user = 'guest'
        # user = 'rodsminer'

        zone = os.environ.get('IRODS_ZONE')
        if user is None:
            user = os.environ.get('IRODS_USER')
        else:
            # build new home
            os.environ['IRODS_HOME'] = '/%s/home/%s' % (zone, user)
        home = os.environ.get('IRODS_HOME')

        ######################
        # identity GSI

        # Move this into certificates.py?
        cdir = Certificates._dir
        cpath = os.path.join(cdir, user)

        os.environ['X509_USER_KEY'] = os.path.join(cpath, 'userkey.pem')
        os.environ['X509_USER_CERT'] = os.path.join(cpath, 'usercert.pem')
        if os.environ.get('X509_CERT_DIR') is None:
            os.environ['X509_CERT_DIR'] = os.path.join(cdir, 'simple_ca')

        self._hostdn = Certificates.get_dn_from_cert(
            user='host', certfilename='hostcert')

        ######################
        # session

        sess = iRODSSession(
            user=user,
            zone=zone,
            # password='thisismypassword',
            # authentication_scheme='password',
            authentication_scheme=os.environ.get('IRODS_AUTHSCHEME'),
            host=os.environ.get('IRODS_HOST'),
            port=os.environ.get('IRODS_PORT'),
            server_dn=self._hostdn,
        )

        # log.pp(sess)
        coll = sess.collections.get(home)
        print("Session", sess, coll)

        for col in coll.subcollections:
            print("COLL", col)

        exit(1)
