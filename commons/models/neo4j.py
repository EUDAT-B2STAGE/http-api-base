# -*- coding: utf-8 -*-

""" Models for graph database """

from __future__ import absolute_import

from neomodel import StringProperty, \
    StructuredNode, RelationshipTo, RelationshipFrom, OneOrMore

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class User(StructuredNode):
    email = StringProperty(required=True, unique_index=True)
    authmethod = StringProperty(required=True)
    password = StringProperty()  # A hash produced by Flask login
#########################################
# TO BE USED INSIDE THE OVERIDED CLASS
    name = StringProperty()
    surname = StringProperty()
# TO BE USED INSIDE THE OVERIDED CLASS
#########################################
    # tokens = RelationshipTo('Tokens', 'EMITTED', cardinality=OneOrMore)
    roles = RelationshipTo('Role', 'ROLE', cardinality=OneOrMore)
    externals = RelationshipTo(
        'ExternalAccounts', 'OAUTH', cardinality=OneOrMore)


# class Tokens(StructuredNode):
#     token = StringProperty(required=True)
#     ttl = StringProperty()
#     emitted_from = RelationshipFrom(User, 'EMITTED', cardinality=OneOrMore)


class Role(StructuredNode):
    name = StringProperty(required=True)
    description = StringProperty(default='No description')
    privileged = RelationshipFrom(User, 'ROLE', cardinality=OneOrMore)


class ExternalAccounts(StructuredNode):
    username = StringProperty(required=True, unique_index=True)
    token = StringProperty(required=True)
    email = StringProperty()
    certificate_cn = StringProperty()
    description = StringProperty(default='No description')
    main_user = RelationshipFrom(User, 'OAUTH', cardinality=OneOrMore)
