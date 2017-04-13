#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

RESTful API Python 3 Flask server

"""

import os
import click
import better_exceptions as be
from flask.cli import FlaskGroup
from rapydo.server import create_app
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


#############################
# Management with click
def init_services(info):
    return create_app(name='Initializing Flask services', init_mode=True)


@click.group(cls=FlaskGroup, create_app=init_services)
def cli():
    """This is a management script for the wiki application."""
    log.debug("Custom command group: %s" % be.__class__)


if __name__ == '__main__':
    # http://flask.pocoo.org/docs/0.12/cli/
    cli()
