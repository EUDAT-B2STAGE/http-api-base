#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

RESTful API Python 3 Flask server

"""

import time
import os
from restapi.utils import myself, lic, PRODUCTION
from restapi.utils.logs import get_logger
from restapi.server import create_app
from restapi.confs.config import SERVER_HOSTS, SERVER_PORT, args

__author__ = myself
__copyright__ = myself
__license__ = lic

log = get_logger(__name__)

enable_debug = False
enable_security = True

if args is not None:
    if args.debug:
        enable_debug = True
        log.warning("Enabling DEBUG mode")
        time.sleep(1)

    if not args.security:
        enable_security = False
        log.warning("No security enabled! Are you really sure?")
        time.sleep(1)

# The connection is HTTP internally to containers
# The proxy will handle HTTPS calls
# We can safely disable HTTPS on OAUTHLIB requests
# http://stackoverflow.com/a/27785830/2114395
if PRODUCTION:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#############################
# BE FLASK
app = create_app(
    name='REST_API', enable_security=enable_security, debug=enable_debug)

if __name__ == "__main__":
    # NOTE: 'threaded' option avoid to see
    # angular request on this server dropping
    # and becoming slow if not totally frozen
    log.info("*** Running Flask!")
    app.run(host=SERVER_HOSTS, port=SERVER_PORT, threaded=True)
