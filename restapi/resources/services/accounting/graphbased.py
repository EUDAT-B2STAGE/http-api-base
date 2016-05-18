# -*- coding: utf-8 -*-

"""
Implement flask login with other services than sqlalchemy

http://blog.miguelgrinberg.com/post/restful-authentication-with-flask
https://github.com/maxcountryman/flask-login/blob/master/flask_login/utils.py#L109
https://github.com/mattupstate/flask-security/blob/develop/flask_security/utils.py#L143


"""

from __future__ import absolute_import

from datetime import datetime
from flask.ext.security.utils import encrypt_password, verify_password
from flask.ext.login import make_secure_token
from ..neo4j.graph import GraphFarm

from .... import get_logger
logger = get_logger(__name__)


# TO FIX withing the Graph
class MyRole(object):
    def __init__(self):
        self.name = 'Admin'


#######################################
# Graph Based
class GraphUser(object):

    def __init__(self, id, email, password, roles):

        self.id = id
        self.roles = roles
        self.email = email
        self.hashed_password = password

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email

    def get_auth_token(self):
        return make_secure_token(
            # Use the encrypted password
            self.hashed_password,
            # Use the time to make the token change
            str(datetime.now()),
            # Key will be the id of the user
            key=str(self.id))

    @staticmethod
    def password_hash(password):
        return encrypt_password(password)

    @staticmethod
    def validate_login(password_hash, password):
        return verify_password(password, password_hash)
        # This does not work, because of the Mac Hash in Flask Security
        # return cls.password_hash(password) == password_hash

    @staticmethod
    def get_user(email=None, token=None):

        if email is None and token is None:
            return None

        g = GraphFarm().get_graph_instance()

        user = None
        try:
            if email is not None:
                user = g.User.nodes.get(email=email)
            if token is not None:
                user = g.User.nodes.get(token=token)
        except g.User.DoesNotExist:
            logger.warning(
                "Could not find user from: (%s, %s)" % (email, token))
            return None

        return user

    @classmethod
    def set_graph_user_token(cls, email, token):
        if token is None:
            return False

        user = cls.get_user(email=email)
        if user is None:
            return False

        user.token = token
        user.save()

    @classmethod
    def get_graph_user(cls, email=None, token=None):
        user = cls.get_user(email, token)
        if user is None:
            return None

        return GraphUser(
            user._id, user.email, user.password,
            [MyRole()])


def load_graph_user(username):
    print("\n\n\n", "LOAD USER? ", username, "\n\n\n")
    logger.critical("Reloading session user with Graphdb and Flask Login!!!")
    return GraphUser.get_graph_user(email=username)


def load_graph_token(token):
    # real version here:
    # http://thecircuitnerd.com/flask-login-tokens/
    return GraphUser.get_graph_user(token=token)


# THE FUNCTION BELOW DOES NOT WORK YET

# def unauthorized_on_graph():
#     # do stuff
#     print("\n\n\n ", "Unauthorized!", "\n\n\n")
#     return "Unauthorized!"
