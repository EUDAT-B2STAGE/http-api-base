# -*- coding: utf-8 -*-

import re
from datetime import datetime
import pytz
from functools import wraps
from neomodel import db as transaction
from py2neo.error import GraphError
from py2neo.cypher.error.schema import ConstraintViolation
from neomodel.exception import RequiredProperty
from neomodel.exception import UniqueProperty
from restapi.resources.exceptions import RestApiException
from restapi.resources.base import ExtendedApiResource
from commons import htmlcodes as hcodes

from commons.logs import get_logger
logger = get_logger(__name__)

__author__ = "Mattia D'Antonio (m.dantonio@cineca.it)"


class GraphBaseOperations(ExtendedApiResource):

    def initGraph(self):
        self.graph = self.global_get_service('neo4j')
        self._current_user = self.getLoggedUserInstance()

    def getSingleLinkedNode(self, relation):

        nodes = relation.all()
        if len(nodes) <= 0:
            return None
        return nodes[0]

    def getLoggedUserInstance(self):
        user = self.get_current_user()
        if user is None:
            return None
        try:
            return self.graph.User.nodes.get(email=user.email)
        except self.graph.User.DoesNotExist:
            return None

    def getNode(self, Model, identifier, field='accession'):

        try:

            if field == 'accession':
                return Model.nodes.get(accession=identifier)

            if field == 'id':
                return Model.nodes.get(id=identifier)

            if field == 'uuid':
                return Model.nodes.get(uuid=identifier)

            if field == 'taxon_id':
                return Model.nodes.get(taxon_id=identifier)

            return Model.nodes.get(accession=identifier)

        except Model.DoesNotExist:
            return None

    def countNodes(self, type):
        query = "MATCH (a: " + type + ") RETURN count(a) as count"

        records = self.graph.cypher(query)
        for record in records:
            if (record is None):
                return 0
            if (record.count is None):
                return 0

        return record.count

    def getCurrentDate(self):
        return datetime.now(pytz.utc)

    # HANDLE INPUT PARAMETERS

    @staticmethod
    def createUniqueIndex(*var):

        separator = "#_#"
        return separator.join(var)

    def readProperty(self, schema, values, checkRequired=True):

        properties = {}
        for field in schema:
            if 'islink' in field:
                continue

            k = field["key"]
            if k in values:
                properties[k] = values[k]

            # this field is missing but required!
            elif checkRequired and field["required"] == "true":
                raise myGraphError(
                    'Missing field: %s' % k,
                    status_code=hcodes.HTTP_BAD_REQUEST)

        return properties

    def updateProperties(self, instance, schema, properties):

        for field in schema:
            if 'islink' in field:
                continue
            key = field["key"]
            if key in properties:
                instance.__dict__[key] = properties[key]

    def parseAutocomplete(
            self, properties, key, id_key='value', split_char=None):
        value = properties.get(key, None)

        ids = []

        if value is None:
            return ids

        # Multiple autocomplete
        if type(value) is list:
            for v in value:
                if v is None:
                    return None
                if id_key in v:
                    ids.append(v[id_key])
                else:
                    ids.append(v)
            return ids

        # Single autocomplete
        if id_key in value:
            return [value[id_key]]

        # Command line input
        if split_char is None:
            return [value]

        return value.split(split_char)


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
