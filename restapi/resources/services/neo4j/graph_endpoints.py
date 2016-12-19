# -*- coding: utf-8 -*-

import re
from functools import wraps
from neomodel import db as transaction
from py2neo.error import GraphError
from py2neo.cypher.error.schema import ConstraintViolation
from neomodel.exception import RequiredProperty
from neomodel.exception import UniqueProperty
from restapi.resources.exceptions import RestApiException
from commons import htmlcodes as hcodes

from commons.logs import get_logger
logger = get_logger(__name__)

__author__ = "Mattia D'Antonio (m.dantonio@cineca.it)"


class myGraphError(RestApiException):
    status_code = None

    def __init__(self, exception, status_code=hcodes.HTTP_BAD_NOTFOUND):
        super(myGraphError).__init__()
        self.status_code = status_code


def returnError(self, label, error, code=hcodes.HTTP_BAD_NOTFOUND):
    error = str(error)
    logger.error(error)
    return self.force_response(errors={label: error}, code=code)


def graph_transactions(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):

        try:

            logger.debug("Neomodel transaction BEGIN")
            transaction.begin()

            out = func(self, *args, **kwargs)

            logger.debug("Neomodel transaction COMMIT")
            transaction.commit()

            return out
        except Exception as e:
            logger.debug("Neomodel transaction ROLLBACK")
            try:
                # Starting from neo4j 2.3.0 ClientErrors automatically
                # rollback transactions and raise a 404 error:
                # HTTP DELETE returned response 404
                # https://github.com/neo4j/neo4j/issues/5806

                transaction.rollback()
            except Exception as rollback_exp:
                logger.warning(
                    "Exception raised during rollback: %s" % rollback_exp)
            raise e

    return wrapper


def catch_graph_exceptions(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):

        try:
            return func(self, *args, **kwargs)
        except (myGraphError) as e:
            if e.status_code == hcodes.HTTP_BAD_FORBIDDEN:
                label = 'Forbidden'
            elif e.status_code == hcodes.HTTP_BAD_NOTFOUND:
                label = 'Not found'
            else:
                label = 'Bad request'
            return returnError(self, label, e, code=e.status_code)

        except (UniqueProperty) as e:

            prefix = "Node [0-9]+ already exists with label"
            regExpr = "%s (.+) and property (.+)" % prefix
            m = re.search(regExpr, str(e))
            if m:
                node = m.group(1)
                prop = m.group(2)
                parsedError = "A %s already exist with %s" % (node, prop)
            else:
                parsedError = e

            return returnError(
                self, 'Duplicated property',
                parsedError, code=hcodes.HTTP_BAD_CONFLICT)
        except ConstraintViolation as e:
            return returnError(self, 'DB', e)
        except (GraphError) as e:
            # Also returned for duplicated fields...
            # UniqueProperty not catched?
            return returnError(self, 'DB', e)
        except (RequiredProperty) as e:
            return returnError(self, 'DB', e)

    return wrapper
