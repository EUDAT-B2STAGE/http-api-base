# -*- coding: utf-8 -*-

""" Models for the relational database """

from __future__ import absolute_import
from ..databases.alchemy import db

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


####################################
# Define multi-multi relation
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


####################################
# Define models
class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return "[db model: %s] %s" % (self.__class__.__name__, self.name)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # name = db.Column(db.String(255))
    # surname = db.Column(db.String(255))
    email = db.Column(db.String(100), unique=True)
    authmethod = db.Column(db.String(20))
    password = db.Column(db.String(255))
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return "[db model: %s] %s" % (self.__class__.__name__, self.email)


# class ExternalAccounts(db.Model):
#     username = db.Column(db.String(60), primary_key=True)
# # TEXT?
#     token = db.Column(db.String(255))
#     email = db.Column(db.String(255))
#     certificate_cn = db.Column(db.String(255))
#     description = db.Column(db.String(255))

#     def __str__(self):
#         return "[db model: %s] %s" % (self.__class__.__name__, self.email)
