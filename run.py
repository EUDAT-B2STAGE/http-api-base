#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

RESTful API Python 3 Flask server

"""

import os
import better_exceptions as be
from rapydo.confs import PRODUCTION
from rapydo.utils.logs import get_logger
from rapydo.server import create_app

## HOST and PORT to be setted for Flask command outside
from rapydo.confs import SERVER_HOSTS, SERVER_PORT

log = get_logger(__name__)

# The connection is HTTP internally to containers
# The proxy will handle HTTPS calls
# We can safely disable HTTPS on OAUTHLIB requests
# http://stackoverflow.com/a/27785830/2114395
if PRODUCTION:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#############################
# BE FLASK
app = create_app(name='REST_API')

if __name__ == "__main__":
    # NOTE: 'threaded' option avoid to see
    # angular request on this server dropping
    # and becoming slow if not totally frozen
    log.info("Flask server is running. Loaded %s" % be)
## THREADED option to be set from command line?
    app.run(host=SERVER_HOSTS, port=SERVER_PORT, threaded=True,
##REMOVE ME
        debug=True)
