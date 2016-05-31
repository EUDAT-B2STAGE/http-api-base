# -*- coding: utf-8 -*-

"""

Move here the logic for any logs

"""

import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

OBSCURED_FIELDS = ['password', 'pwd', 'token']


def obscure_passwords(original_parameters_string):

    """ Avoid printing passwords! """
    if (original_parameters_string is None):
        return {}

    mystr = original_parameters_string.decode("ascii")
    if mystr.strip() == '':
        return {}

    parameters = json.loads(mystr)
    for key, value in parameters.items():
        if key in OBSCURED_FIELDS:
            value = '****'
        parameters[key] = value
    return parameters
