# -*- coding: utf-8 -*-

"""
Base Models for mongo database.

See
https://pymodm.readthedocs.io/en/stable/api/index.html
    #pymodm.base.fields.MongoBaseField

And
https://docs.mongodb.com/manual/applications/data-models-relationships
"""

from pymongo.write_concern import WriteConcern
from pymodm import MongoModel, fields
from commons.services.uuid import getUUID


# TO FIX: inheritance?
# ####################
# # Templates
# class AuthModel(MongoModel):

#     class Meta:
#         write_concern = WriteConcern(j=True)
#         connection_alias = 'auth'


# class AuthModelWithUuid(AuthModel):

#     uuid = fields.UUIDField()


####################
# Base Models
class Role(MongoModel):
    name = fields.CharField(primary_key=True)
    description = fields.CharField()

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'


class User(MongoModel):
    email = fields.EmailField(primary_key=True)
    uuid = fields.UUIDField(default=getUUID())
    name = fields.CharField()
    surname = fields.CharField()
    authmethod = fields.CharField()
    password = fields.CharField(required=True)
    roles = fields.EmbeddedDocumentListField(Role)

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'


class Token(MongoModel):
    jti = fields.CharField()
    token = fields.CharField()
    creation = fields.DateTimeField()
    expiration = fields.DateTimeField()
    last_access = fields.DateTimeField()
    IP = fields.CharField()
    hostname = fields.CharField()
    user_id = fields.ReferenceField(User)
    emitted_for = fields.EmbeddedDocumentField(User)

    class Meta:
        write_concern = WriteConcern(j=True)
        connection_alias = 'auth'


class ExternalAccounts(MongoModel):
    pass
#     username = db.Column(db.String(60), primary_key=True)
#     token = db.Column(db.Text())
#     token_expiration = db.Column(db.DateTime)
#     email = db.Column(db.String(255))
#     certificate_cn = db.Column(db.String(255))
#     certificate_dn = db.Column(db.Text())
#     proxyfile = db.Column(db.Text())
#     description = db.Column(db.String(255))
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
# # Note: for pre-production release
# # we allow only one external account per local user
#     main_user = db.relationship(
#         'User', backref=db.backref('authorization', lazy='dynamic'))

    # class Meta:
    #     write_concern = WriteConcern(j=True)
    #     connection_alias = 'auth'
