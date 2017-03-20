# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
from flask import request
from urllib.parse import urlparse
#######################

AVOID_COLORS_ENV_LABEL = 'TESTING_FLASK'
STACKTRACE = False
REMOVE_DATA_AT_INIT_TIME = False

#################################
# ENDPOINTS bases
API_URL = '/api'
AUTH_URL = '/auth'
STATIC_URL = '/static'
BASE_URLS = [API_URL, AUTH_URL]

#################################
# Directories for core code or user custom code
BACKEND_PACKAGE = 'rapydo'
CUSTOM_PACKAGE = os.environ.get('VANILLA_PACKAGE', 'custom')

CORE_CONFIG_PATH = os.path.join(BACKEND_PACKAGE, 'confs')

# DEFAULTS_PATH = os.path.join(BACKEND_PACKAGE, 'confs', 'defaults')

BLUEPRINT_KEY = 'blueprint'

# NOTE: this decides about final configuration
DEBUG = True

#################################
# THE APP

# DEBUG = os.environ.get('API_DEBUG', default_debug)
DEBUG = os.environ.get('API_DEBUG', None)

PRODUCTION = False
if os.environ.get('APP_MODE', '') == 'production':
    PRODUCTION = True

###################################################
###################################################
SERVER_HOSTS = '0.0.0.0'
TEST_HOST = 'localhost'
SERVER_PORT = int(os.environ.get('PORT', 5000))

USER_HOME = os.environ['HOME']

###################
UPLOAD_FOLDER = '/uploads'

SECRET_KEY_FILE = "/jwt_tokens/secret.key"

#################################
# SQLALCHEMY
BASE_DB_DIR = '/dbs'
SQLLITE_EXTENSION = 'db'
SQLLITE_DBFILE = 'backend' + '.' + SQLLITE_EXTENSION
dbfile = os.path.join(BASE_DB_DIR, SQLLITE_DBFILE)
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + dbfile


########################################
def get_api_url():
    """ Get api URL and PORT

    Usefull to handle https and similar
    unfiltering what is changed from nginx and container network configuration

    Warning: it works only if called inside a Flask endpoint
    """

    api_url = request.url_root

    if PRODUCTION:
        parsed = urlparse(api_url)
        if parsed.port is not None and parsed.port == 443:
            backend_port = parsed.port
            removed_port = re.sub(r':[\d]+$', '', parsed.netloc)
            api_url = parsed._replace(
                scheme="https", netloc=removed_port
            ).geturl()

    return api_url, backend_port

#############################
# Command line arguments


def my_cli_arguments():

    # TO FIX: use flask cli or flask-script

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
