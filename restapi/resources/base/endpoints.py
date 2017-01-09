# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import

from ..rest.definition import EndpointResource
from ...confs.config import AUTH_URL
from ...auth import authentication
from ...confs import config
from ..services.detect import CELERY_AVAILABLE
from ..services.authentication import BaseAuthentication
from .. import decorators as decorate
from flask import jsonify, current_app
from commons import htmlcodes as hcodes
# from commons.swagger import swagger
from commons.logs import get_logger  # , pretty_print

log = get_logger(__name__)


class Status(EndpointResource):
    """ API online client testing """

    def get(self):
        return 'Server is alive!'


class SwaggerSpecifications(EndpointResource):
    """
    Specifications output throught Swagger (open API) standards
    """

    def get(self):

        # # find the package root to read swagger
        # root = __package__.split('.')[0]
        # # Enable swagger
        # swag = swagger(current_app,
        #                package_root=root, from_file_keyword='swag_file')
        # # Build the output
        # return jsonify(swag)

        # NOTE: swagger dictionary is read only once, at server init time
        from commons.globals import mem
        # Jsonify, so we skip custom response building
        return jsonify(mem.swagger_definition)


class Login(EndpointResource):
    """ Let a user login with the developer chosen method """

    def post(self):

        # NOTE: In case you need different behaviour when using unittest
        # if current_app.config['TESTING']:
        #     print("\nThis is inside a TEST\n")

        username = None
        password = None
        bad_code = hcodes.HTTP_BAD_UNAUTHORIZED

        jargs = self.get_input()
        if 'username' in jargs:
            username = jargs['username']
        elif 'email' in jargs:
            username = jargs['email']
        if 'password' in jargs:
            password = jargs['password']
        elif 'pwd' in jargs:
            password = jargs['pwd']

        if username is None or password is None:
            return self.send_errors(
                "Credentials", "Missing 'username' and/or 'password'",
                code=bad_code)

        # auth instance from the global namespace
        auth = self.global_get('custom_auth')
        token, jti = auth.make_login(username, password)
        if token is None:
            return self.send_errors(
                "Credentials", "Invalid username and/or password",
                code=bad_code)

        auth.save_token(auth._user, token, jti)

        # TO FIX: split response as above in access_token and token_type?
        # # The right response should be the following
        # return self.force_response({
        #     'access_token': token,
        #     'token_type': auth.token_type
        # })
        # OR
        # {
        #   "scope": "https://b2stage.cineca.it/api/.*",
        #   "access_token": "EEwJ6tF9x5WCIZDYzyZGaz6Khbw7raYRIBV_WxVvgmsG",
        #   "token_type": "Bearer",
        #   "user": "pippo",
        #   "expires_in": 28800
        # }
        # TO FIX: also set headers

        return {'token': token}


class Logout(EndpointResource):
    """ Let the logged user escape from here, invalidating current token """

    def get(self):
        auth = self.global_get('custom_auth')
        auth.invalidate_token(auth.get_token())
        return self.empty_response()


class Tokens(EndpointResource):
    """ List all active tokens for a user """

    @decorate.add_endpoint_parameter('user')
    def get(self, token_id=None):

        auth = self.global_get('custom_auth')
        iamadmin = auth.verify_admin()
        current_user = self.get_current_user()
        if iamadmin:
            user = self.get_input(single_param='user', default=current_user)
        else:
            user = current_user

        tokens = auth.get_tokens(user=user)

        if token_id is None:
            return tokens

        for token in tokens:
            if token["id"] == token_id:
                return token

        errorMessage = "This token has not emitted to your account " + \
                       "or does not exist"
        return self.send_errors(
            "Token not found", errorMessage, code=hcodes.HTTP_BAD_NOTFOUND)

    @decorate.add_endpoint_parameter('user')
    def delete(self, token_id=None):
        """
            For additional security, tokens are invalidated both
            by chanding the user UUID and by removing single tokens
        """

        auth = self.global_get('custom_auth')
        iamadmin = auth.verify_admin()
        current_user = self.get_current_user()
        if iamadmin:
            user = self.get_input(single_param='user', default=current_user)
        else:
            user = current_user

        tokens = auth.get_tokens(user=user)
        invalidated = False

        for token in tokens:
            # all or specific
            if token_id is None or token["id"] == token_id:
                done = auth.invalidate_token(token=token["token"], user=user)
                if not done:
                    return self.send_errors("Failed", "token: '%s'" % token)
                else:
                    log.debug("Invalidated %s" % token['id'])
                    invalidated = True

        # Check

        # ALL
        if token_id is None:
            # NOTE: this is allowed only in removing tokens in unittests
            if not current_app.config['TESTING']:
                raise KeyError("Please specify a valid token")
            auth.invalidate_all_tokens(user=user)
        # SPECIFIC
        else:
            if not invalidated:
                message = "Not emitted for your account or does not exist"
                return self.send_errors(
                    "Token not found", message, code=hcodes.HTTP_BAD_NOTFOUND)

        return self.empty_response()


# class AdminTokens(EndpointResource):
#     """ Admin operations on token list """

#     base_url = AUTH_URL
#     endkey = "token_id"
#     endtype = "string"

#     @authentication.authorization_required(roles=[config.ROLE_ADMIN])
#     def get(self, token_id):
#         auth = self.global_get('custom_auth')
#         token = auth.get_tokens(token_jti=token_id)
#         if len(token) == 0:
#             return self.send_errors(
#                 "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)
#         return token

#     @authentication.authorization_required(roles=[config.ROLE_ADMIN])
#     def delete(self, token_id):
#         auth = self.global_get('custom_auth')
#         if not auth.destroy_token(token_id):
#             return self.send_errors(
#                 "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)

#         return self.empty_response()


class Profile(EndpointResource):
    """ Current user informations """

    base_url = AUTH_URL

    @authentication.authorization_required
    def get(self):
        """
        Token authentication tester. Example of working call is: 
        http localhost:8081/auth/profile
            Authorization:"Bearer RECEIVED_TOKEN"
        """

        auth = self.global_get('custom_auth')
        data = {}
        data["status"] = "Valid user"
        data["email"] = auth._user.email

        roles = []
        for role in auth._user.roles:
            roles.append(role.name)
        data["roles"] = roles

        if hasattr(auth._user, 'name'):
            data["name"] = auth._user.name

        if hasattr(auth._user, 'surname'):
            data["surname"] = auth._user.surname

        if hasattr(auth._user, 'irods_user'):
            data["irods_user"] = auth._user.irods_user

        return data

    @authentication.authorization_required
    def put(self):

        from flask_restful import request
        try:
            data = request.get_json(force=True)

            if "newpassword" not in data:
                return self.send_errors(
                    "Error",
                    "Invalid request, this operation cannot be completed",
                    code=hcodes.HTTP_BAD_REQUEST
                )
            user = self.get_current_user()
            pwd = BaseAuthentication.hash_password(data["newpassword"])
            user.password = pwd
            user.save()
            auth = self.global_get('custom_auth')
            tokens = auth.get_tokens(user=auth._user)

            for token in tokens:
                auth.invalidate_token(token=token["token"])
            auth.invalidate_all_tokens()

        except:
            return self.send_errors(
                "Error",
                "Unknown error, please contact system administrators",
                code=hcodes.HTTP_BAD_REQUEST
            )

        return self.empty_response()


class Internal(EndpointResource):
    """ Token and Role authentication test """

    base_url = AUTH_URL

    @authentication.authorization_required(roles=[config.ROLE_INTERNAL])
    def get(self):
        return "I am internal"


class Admin(EndpointResource):
    """ Token and Role authentication test """

    base_url = AUTH_URL

    @authentication.authorization_required(roles=[config.ROLE_ADMIN])
    def get(self):
        return "I am admin!"


# In case you have celery queue,
# you get a queue endpoint for free
if CELERY_AVAILABLE:
    from commons.services.celery import celery_app

    class Queue(EndpointResource):

        endkey = "task_id"
        endtype = "string"

        @authentication.authorization_required(roles=[config.ROLE_ADMIN])
        def get(self, task_id=None):

            # Inspect all worker nodes
            workers = celery_app.control.inspect()

            data = []

            active_tasks = workers.active()
            revoked_tasks = workers.revoked()
            scheduled_tasks = workers.scheduled()

            for worker in active_tasks:
                tasks = active_tasks[worker]
                for task in tasks:
                    if task_id is not None and task["id"] != task_id:
                        continue

                    row = {}
                    row['status'] = 'ACTIVE'
                    row['worker'] = worker
                    row['ETA'] = task["time_start"]
                    row['task_id'] = task["id"]
                    row['task'] = task["name"]
                    row['args'] = task["args"]

                    if task_id is not None:
                        task_result = celery_app.AsyncResult(task_id)
                        row['task_status'] = task_result.status
                        row['info'] = task_result.info
                    data.append(row)

            for worker in revoked_tasks:
                tasks = revoked_tasks[worker]
                for task in tasks:
                    if task_id is not None and task != task_id:
                        continue
                    row = {}
                    row['status'] = 'REVOKED'
                    row['task_id'] = task
                    data.append(row)

            for worker in scheduled_tasks:
                tasks = scheduled_tasks[worker]
                for task in tasks:
                    if task_id is not None and \
                       task["request"]["id"] != task_id:
                        continue

                    row = {}
                    row['status'] = 'SCHEDULED'
                    row['worker'] = worker
                    row['ETA'] = task["eta"]
                    row['task_id'] = task["request"]["id"]
                    row['priority'] = task["priority"]
                    row['task'] = task["request"]["name"]
                    row['args'] = task["request"]["args"]
                    data.append(row)

            # from celery.task.control import inspect
            # tasks = inspect()

            return self.force_response(data)

        # @authentication.authorization_required(roles=[config.ROLE_ADMIN])
        # def put(self, task_id):
        #     from celery.task.control import revoke
        #     revoke(task_id, terminate=True)
        #     return self.force_response("!")

        @authentication.authorization_required(roles=[config.ROLE_ADMIN])
        def put(self, task_id):
            celery_app.control.revoke(task_id)
            return self.empty_response()

        @authentication.authorization_required(roles=[config.ROLE_ADMIN])
        def delete(self, task_id):
            celery_app.control.revoke(task_id, terminate=True)
            return self.empty_response()
