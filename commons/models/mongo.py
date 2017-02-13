# -*- coding: utf-8 -*-

""" Base Models for mongo database """

from pymongo.write_concern import WriteConcern
from pymodm import MongoModel, fields


class User(MongoModel):
    # # uuid = StringProperty(required=True, unique_index=True)
    # email = EmailProperty(required=True, unique_index=True, show=True)
    email = fields.EmailField()
    test = fields.CharField()
    # name = StringProperty(required=True, show=True)
    # surname = StringProperty(required=True, show=True)
    # authmethod = StringProperty(required=True)
    # password = StringProperty()  # Hashed from a custom function
    # tokens = RelationshipTo('Token', 'HAS_TOKEN', cardinality=ZeroOrMore)
    # roles = RelationshipTo(
    #     'Role', 'HAS_ROLE', cardinality=ZeroOrMore, show=True)
    # externals = RelationshipTo(
    #     'ExternalAccounts', 'HAS_AUTHORIZATION', cardinality=OneOrMore)

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'
