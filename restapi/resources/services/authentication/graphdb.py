# -*- coding: utf-8 -*-

"""
Implement authentication with graphdb as user database

How to delete the whole db:
MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r
"""

from __future__ import absolute_import

from datetime import datetime
# from flask.ext.security.utils import encrypt_password, verify_password
# from flask.ext.login import make_secure_token
# from confs.config import USER, PWD, ROLE_ADMIN, ROLE_USER

from .generic import BaseAuthentication
from ..neo4j.graph import GraphFarm

from .... import get_logger
logger = get_logger(__name__)


class Authentication(BaseAuthentication):

    def __init__(self):
        self._graph = GraphFarm().get_graph_instance()

    def get_user_object(self, username):

        user = None
        g = GraphFarm().get_graph_instance()
        try:
            user = g.User.nodes.get(email=username)
        except g.User.DoesNotExist:
            logger.warning("Could not find user for '%s'" % username)
        return user

    def fill_payload(self, userobj):
        return {
            'user_id': userobj._id,
            'hpwd': userobj.password,
            'emitted': str(datetime.now())
        }

    def init_users_and_roles(self):

        if not len(self._graph.Role.nodes) > 0:
            logger.warning("No roles inside graphdb. Injected defaults.")
            for role in self.DEFAULT_ROLES:
                role = self._graph.Role(name=role, description="automatic")
                role.save()

        if not len(self._graph.User.nodes) > 0:
            logger.warning("No users inside graphdb. Injected default.")
            user = self._graph.User(
                email=self.DEFAULT_USER,
                name='Default', surname='User',
                password=self.hash_password(self.DEFAULT_PASSWORD))
            user.save()

            for role in self.DEFAULT_ROLES:
                role_obj = self._graph.Role.nodes.get(name=role)
                user.roles.connect(role_obj)

"""

# MAKE THIS WORK WITH JWT
class MyGraphLogin(ExtendedApiResource, GraphFarm):

    def get(self):
        return "Hello World! I need user and pwd via POST :-)"

    # @decorate.apimethod
    def post(self):

        from flask.ext.restful import request
        from flask.ext.login import login_user
        from ..services.accounting.graphbased import UserModel

        j = request.get_json(force=True)
        if 'username' not in j or 'password' not in j:
            return self.response(
                errors={'Missing credentials':
                        'you need to specify username and password'})

        user, token = \
            UserModel.emit_token_from_credentials(j['username'], j['password'])

        # In case something is wrong
        if user is None or token is None:
            return self.response(errors={
                'Invalid credentials': 'wrong username or password'},
                code=hcodes.HTTP_BAD_UNAUTHORIZED)

        # Save the user for flask login sessions
        login_user(user)

        return self.response({'Authentication-token': token})


#######################################
# Graph Based
class UserModel(object):

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

        payload = {
            'user_id': self.id,
            'hpwd': self.hashed_password,
            'emitted': str(datetime.now())
        }

        # JWT token
        byte_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        return byte_token.decode()

        # Normal token
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
# USE JWT
            if token is not None:
                print("TOKEN IS", token)
                import jwt
                payload = jwt.decode(
                    token, JWT_SECRET, algorithms=[JWT_ALGO])
                print("TEST", payload)
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

        # Get connected roles
        roles = []
        for role in user.roles.all():
            roles.append(role)
            # roles.append({'name': role.name})
        return UserModel(user._id, user.email, user.password, roles)

    def emit_token_from_credentials(auth_user, auth_pwd):
        user = UserModel.get_graph_user(email=auth_user)
        token = None

        # Check password and create token if fine
        if user is not None:
            # Validate password
            if UserModel.validate_login(
               user.hashed_password, auth_pwd):

                logger.info("Validated credentials")

                # Create a new token and save it
                token = user.get_auth_token()
# USE JWT and DO NOT SAVE INSIDE THE DATABASE
                UserModel.set_graph_user_token(auth_user, token)
        return (user, token)


def load_graph_user(username):
    print("\n\n\n", "LOAD USER? ", username, "\n\n\n")
    logger.critical("Reloading session user with Graphdb and Flask Login!!!")
    return UserModel.get_graph_user(email=username)


def load_graph_token(token):

# CHECK TTL?

    # real version here:
    # http://thecircuitnerd.com/flask-login-tokens/
    return UserModel.get_graph_user(token=token)


# THE FUNCTION BELOW DOES NOT WORK YET

# def unauthorized_on_graph():
#     # do stuff
#     print("\n\n\n ", "Unauthorized!", "\n\n\n")
#     return "Unauthorized!"


#######################################
# INIT
def _create_default_graph_roles(graph):

    roles = []
    main_role = graph.Role(name=ROLE_USER)
    main_role.save()
    roles.append(main_role)
    admin_role = graph.Role(name=ROLE_ADMIN)
    admin_role.save()
    roles.append(admin_role)
    return roles


def _create_default_graph_user(graph, roles):
    user = graph.User(
        name='Default', surname='User', email=USER,
        password=UserModel.password_hash(PWD))
    user.save()
    for role in roles:
        user.roles.connect(role)


def init_graph_accounts():
    g = GraphFarm().get_graph_instance()
    if len(g.Role.nodes) < 1:
        logger.warning("No roles inside graphdb. Injected defaults.")
        roles = _create_default_graph_roles(g)

        if len(g.User.nodes) < 1:
            logger.warning("No users inside graphdb. Injected default.")
            _create_default_graph_user(g, roles)

    # exit(1)

"""
