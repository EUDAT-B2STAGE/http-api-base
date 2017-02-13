# -*- coding: utf-8 -*-

"""
Base Models for mongo database

CharField
NumField?
EmailField
DateTimeField
BooleanField
ReferenceField
EmbeddedDocumentListField

"""

from pymongo.write_concern import WriteConcern
from pymodm import MongoModel, fields


class Role(MongoModel):
    # id = db.Column(db.Integer(), primary_key=True)
    name = fields.CharField(primary_key=True)
    description = fields.CharField()

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'


class User(MongoModel):
    # id = db.Column(db.Integer, primary_key=True)
    email = fields.EmailField(primary_key=True)
    uuid = fields.CharField()  # note: this should be UNIQUE
    name = fields.CharField()
    surname = fields.CharField()
    authmethod = fields.CharField()
    password = fields.CharField()
    roles = fields.EmbeddedDocumentListField(Role)

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'
