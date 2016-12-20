# -*- coding: utf-8 -*-

""" Models for graph database """

from __future__ import absolute_import

from neomodel import StructuredNode, StringProperty, DateTimeProperty, \
    RelationshipTo, RelationshipFrom, \
    OneOrMore, ZeroOrMore, ZeroOrOne
from ..logs import get_logger

logger = get_logger(__name__)


class User(StructuredNode):
    uuid = StringProperty(required=True, unique_index=True)
    email = StringProperty(required=True, unique_index=True)
    authmethod = StringProperty(required=True)
    password = StringProperty()  # Hashed from a custom function
    tokens = RelationshipTo('Token', 'HAS_TOKEN', cardinality=ZeroOrMore)
    roles = RelationshipTo('Role', 'HAS_ROLE', cardinality=ZeroOrMore)
    externals = RelationshipTo(
        'ExternalAccounts', 'HAS_AUTHORIZATION', cardinality=OneOrMore)


class Token(StructuredNode):
    jti = StringProperty(required=True, unique_index=True)
    token = StringProperty(required=True, unique_index=True)
    creation = DateTimeProperty(required=True)
    expiration = DateTimeProperty()
    last_access = DateTimeProperty()
    IP = StringProperty()
    hostname = StringProperty()
    emitted_for = RelationshipFrom('User', 'HAS_TOKEN', cardinality=ZeroOrOne)


class Role(StructuredNode):
    name = StringProperty(required=True, unique_index=True)
    description = StringProperty(default='No description')
    privileged = RelationshipFrom(User, 'HAS_ROLE', cardinality=OneOrMore)

    _fields_to_show = [
        "name", "description"
    ]


class ExternalAccounts(StructuredNode):
    username = StringProperty(required=True, unique_index=True)
    token = StringProperty(required=True)
    email = StringProperty()
    certificate_cn = StringProperty()
    proxyfile = StringProperty()
    description = StringProperty(default='No description')
    main_user = RelationshipFrom(
        User, 'HAS_AUTHORIZATION', cardinality=OneOrMore)
