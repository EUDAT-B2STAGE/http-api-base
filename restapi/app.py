# -*- coding: utf-8 -*-

"""
Flask app creation
"""

from . import myself, lic, get_logger
import time
from .server import create_app
from confs.config import args

__author__ = myself
__copyright__ = myself
__license__ = lic

logger = get_logger(__name__)

enable_debug = False
enable_security = True

if args is not None:
    if args.debug:
        enable_debug = True
        logger.warning("Enabling DEBUG mode")
        time.sleep(1)

    if not args.security:
        enable_security = False
        logger.warning("No security enabled! Are you really sure?")
        time.sleep(1)

#############################
# BE FLASK
if __name__ == "__main__":
    app = create_app(name='API',
                     enable_security=enable_security, debug=enable_debug)
    # We are now ready
    logger.info("*** REST API server is online ***")
