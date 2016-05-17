# -*- coding: utf-8 -*-

"""
Implement flask login with other services than sqlalchemy
"""

from __future__ import absolute_import
from ..neo4j.graph import GraphFarm

from .... import get_logger
logger = get_logger(__name__)


# TO FIX
class MyRole(object):
    def __init__(self):
        self.name = 'Admin'


#######################################
# Graph Based
class GraphUser(object):

    def __init__(self, id, email, roles):

        self.id = id
        self.roles = roles
        self.email = email

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email

    def get_auth_token(self):
        """
        Encode a secure token for cookie
        """
        return "TOKEN-123"

    @staticmethod
    def validate_login(password_hash, password):
        return password == "123"

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

        return GraphUser(user._id, user.email, [MyRole()])


def load_graph_user(username):
    print("\n\n\n", "LOAD USER? ", username, "\n\n\n")

    g = GraphFarm.get_graph_instance()

    #TO BE CHANGED TO USE THE GRAPH
    """
    u = app.config['USERS_COLLECTION'].find_one({"_id": username})
    if not u:
        return None
    return User(u['_id'])
    """
    return None

    # USING THE GRAPH:
    """
    user = graph.User.nodes.filter(email=username)
    for u in user.all():
        return User(u._id)
    """


def load_graph_token(token):
    # real version here:
    # http://thecircuitnerd.com/flask-login-tokens/
    return GraphUser.get_graph_user(token=token)


# def unauthorized_on_graph():
#     # do stuff
#     print("\n\n\n ", "Unauthorized!", "\n\n\n")
#     return "Unauthorized!"
