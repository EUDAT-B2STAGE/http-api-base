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


def load_yaml_file(file, path=None, first_doc=False, skip_error=False):
    """ Import data from a YAML file """

    error = None
    if path is None:
        filepath = file
    else:
        filepath = os.path.join(path, file + "." + YAML_EXT)
    log.debug("Reading file %s" % filepath)

    # load from this file
    if os.path.exists(filepath):
        with open(filepath) as fh:
            try:
                # LOAD fails if more than one document is there
                # return yaml.load(fh)
                # LOAD ALL gets more than one document inside the file
                gen = yaml.load_all(fh)
                docs = list(gen)
                if first_doc:
                    if len(docs) > 0:
                        return docs[0]
                    else:
                        raise AttributeError("Missing YAML first document")
                else:
                    return docs
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
