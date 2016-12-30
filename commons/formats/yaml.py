# -*- coding: utf-8 -*-

"""
Loading YAML format
"""

from __future__ import absolute_import

import yaml
import os

from ..logs import get_logger
log = get_logger(__name__)

YAML_EXT = 'yaml'
yaml.dump({})


def load_yaml_file(file, path=None, skip_error=False):
    """ Import data from a YAML file """

    if path is None:
        filepath = file
    else:
        filepath = os.path.join(path, file + "." + YAML_EXT)
    log.debug("Reading file %s" % filepath)

    # load from this file
    if os.path.exists(filepath):
        with open(filepath) as fh:
            try:
                return yaml.load(fh)
            except yaml.composer.ComposerError as e:
                try:
                    fh.seek(0)
# WHAT IF ALWAYS LOAD ALL?
                    docs = yaml.load_all(fh)
                    return list(docs)
                except Exception as e:
                    error = e
            except Exception as e:
                error = e
    else:
        error = 'File does not exist'

    message = "Failed to read YAML from '%s':\n%s" % (filepath, error)
    if skip_error:
        log.error(message)
    else:
        raise Exception(message)
    return None
