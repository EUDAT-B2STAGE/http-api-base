# -*- coding: utf-8 -*-

"""
User configuration
"""

# from __future__ import absolute_import

import os
import sys
import argparse

#################################
# what you could change
STACKTRACE = False
REMOVE_DATA_AT_INIT_TIME = False


#############################
# Command line arguments

def my_cli_arguments():
    arg = argparse.ArgumentParser(description='REST API server based on Flask')
    arg.add_argument("--no-security", action="store_false", dest='security',
                     help='force removal of login authentication on resources')
    arg.add_argument("--debug", action="store_true", dest='debug',
                     help='enable debugging mode')
    arg.add_argument(
        "--remove-old", action="store_true", dest='rm',
        help='force removal of previous new tables')
    arg.set_defaults(security=True, debug=False)
    return arg.parse_args()


args = None
default_debug = False

is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
is_nose = "nose" in sys.modules.keys()
is_nose2 = "nose2" in sys.modules.keys()
is_celery = "celery" in sys.modules.keys()

if not is_gunicorn and not is_nose and not is_nose2 and not is_celery:
    args = my_cli_arguments()
    default_debug = args.debug

###################################################
###################################################
SERVER_HOSTS = '0.0.0.0'
TEST_HOST = 'localhost'
SERVER_PORT = int(os.environ.get('PORT', 5000))

# TRAP_BAD_REQUEST_ERRORS = True
# PROPAGATE_EXCEPTIONS = False

# I am inside the conf dir.
# The base dir is one level up from here
# BASE_DIR = re.sub(__package__, '', os.path.abspath(os.path.dirname(__file__)))
USER_HOME = os.environ['HOME']

###################
# Uploads
# MAX_CONTENT_LENGTH = 128 * (1024 * 1024)  # 128MB
UPLOAD_FOLDER = '/uploads'
# INTERPRETER = 'python3'
# PY2_INTERPRETER = 'python2'

SECRET_KEY_FILE = "/jwt_tokens/secret.key"

#################################
# SQLALCHEMY
BASE_DB_DIR = '/dbs'
SQLLITE_EXTENSION = 'db'
SQLLITE_DBFILE = 'backend' + '.' + SQLLITE_EXTENSION
dbfile = os.path.join(BASE_DB_DIR, SQLLITE_DBFILE)
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + dbfile
# SQLALCHEMY_TRACK_MODIFICATIONS = False
