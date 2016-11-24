# -*- coding: utf-8 -*-

"""
User configuration
"""

import os
import re
import sys
import argparse

#################################
# what you could change
STACKTRACE = False
REMOVE_DATA_AT_INIT_TIME = False
USER = 'user@nomail.org'
PWD = 'test'


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

# Use this to specifiy endpoints based on your resources module
REST_CONFIG_DIR = 'endpoints'
REST_CONFIG_INIT = 'api_init.json'

TRAP_BAD_REQUEST_ERRORS = True
PROPAGATE_EXCEPTIONS = False

# System ROLES
ROLE_ADMIN = 'admin_root'
ROLE_INTERNAL = 'staff_user'
ROLE_USER = 'normal_user'

# I am inside the conf dir.
# The base dir is one level up from here
BASE_DIR = re.sub(__package__, '', os.path.abspath(os.path.dirname(__file__)))
USER_HOME = os.environ['HOME']

###################
# Uploads
# ## default no limits
#MAX_CONTENT_LENGTH = 128 * (1024 * 1024)  # 128MB
UPLOAD_FOLDER = '/uploads'
INTERPRETER = 'python3'
PY2_INTERPRETER = 'python2'

#################################
# SQLALCHEMY
BASE_DB_DIR = '/dbs'
SQLLITE_EXTENSION = 'db'
SQLLITE_DBFILE = 'backend' + '.' + SQLLITE_EXTENSION
dbfile = os.path.join(BASE_DB_DIR, SQLLITE_DBFILE)
SECRET_KEY = 'simplesecret'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + dbfile
SQLALCHEMY_TRACK_MODIFICATIONS = False

# extra
SQLLITE_FRONTEND_DBFILE = 'frontend' + '.' + SQLLITE_EXTENSION
dbfrontendfile = os.path.join(BASE_DB_DIR, SQLLITE_FRONTEND_DBFILE)
SQLALCHEMY_FRONTEND_DATABASE_URI = 'sqlite:///' + dbfrontendfile

#################################
# SECURITY

# Bug fixing for csrf problem via CURL/token
WTF_CSRF_ENABLED = False
# Force token to last not more than one day
SECURITY_TOKEN_MAX_AGE = 3600 * 24
# Add security to password
# https://pythonhosted.org/Flask-Security/configuration.html
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "thishastobelongenoughtosayislonglongverylong"

SECURITY_REGISTERABLE = True
SECURITY_CONFIRMABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
#SECURITY_TRACKABLE

#################################
# ENDPOINTS
API_URL = '/api'
AUTH_URL = '/auth'

# IRODS 4
IRODS_HOME = os.path.join(USER_HOME, ".irods")
if not os.path.exists(IRODS_HOME):
    os.mkdir(IRODS_HOME)
IRODS_ENV = os.path.join(IRODS_HOME, "irods_environment.json")
# IRODS_ENV = USER_HOME + "/.irods/.irodsEnv"

#################################
# THE APP

# DEBUG = os.environ.get('API_DEBUG', default_debug)
DEBUG = os.environ.get('API_DEBUG', None)
#DEBUG = True

PRODUCTION = False
if os.environ.get('APP_MODE', '') == 'production':
    PRODUCTION = True
