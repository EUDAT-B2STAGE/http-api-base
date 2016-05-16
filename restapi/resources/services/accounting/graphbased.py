# -*- coding: utf-8 -*-

"""
Implement flask login with other services than sqlalchemy
"""

from __future__ import absolute_import
from ..neo4j.graph import GraphFarm

from .... import get_logger
logger = get_logger(__name__)


#######################################
# Graph Based
class GraphUser():

    def __init__(self, username):
        self.username = username
        self.token = "TOKEN-123"

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def get_auth_token(self):
        """
        Encode a secure token for cookie
        """
        return "TOKEN-123"

    @staticmethod
    def validate_login(password_hash, password):
        return password =="123"


def load_graph_user(username):
    print("\n\n\n", "LOAD USER? ", username, "\n\n\n")

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

    print("\n\n\n ", token, "\n\n\n")

    # real version here:
    # http://thecircuitnerd.com/flask-login-tokens/

    return User(5)
    #if not => return None


def unauthorized_on_graph():
    # do stuff
    print("\n\n\n ", "Unauthorized!", "\n\n\n")
    return "Unauthorized!"
