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
# from . import decorators as decorate
from flask import jsonify, current_app
from commons import htmlcodes as hcodes
from commons.swagger import swagger
from commons.logs import get_logger

logger = get_logger(__name__)


class Status(EndpointResource):
    """
        API online test
    """

    def get(self):
        """
        Check if the API server is currently reachable

        You may use this URI to monitor network or server problems.
        ---
        tags:
          - status
        responses:
          200:
            description: Server is alive!
        """
        return 'Server is alive!'


class Spec(EndpointResource):
    """
    Specifications output throught Swagger (open API) standards
    """

    def get(self):
        root = __package__.split('.')[0]
        # Enable swagger
        swag = swagger(current_app,
                       package_root=root, from_file_keyword='swag_file')

        from commons.globals import mem
        swag['info']['version'] = mem.custom_config['project']['version']
        swag['info']['title'] = mem.custom_config['project']['title']

        # Build the output
        return jsonify(swag)


class Login(EndpointResource):
    """ Let a user login with the developer chosen method """

    base_url = AUTH_URL

    # @decorate.apimethod
    # def get(self):
    #     return self.send_errors(
    #         "Wrong method", "Please login with the POST method",
    #         code=hcodes.HTTP_BAD_UNAUTHORIZED)

    def post(self):

        # # In case you need different behaviour when using unittest:
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

## // TO FIX
# split response as above in access_token and token_type?
# also set headers?
        # # The right response should be the following
        # # Just remove the simple response above
        # return self.force_response({
        #     'access_token': token,
        #     'token_type': auth.token_type
        # })

        """
        e.g.
{
  "scope": "https://b2stage.cineca.it/api/.*",
  "access_token": "EEwJ6tF9x5WCIZDYzyZGaz6Khbw7raYRIBV_WxVvgmsG",
  "token_type": "Bearer",
  "user": "pippo",
  "expires_in": 28800
}
        """

        return {'token': token}


class Logout(EndpointResource):
    """ Let the logged user escape from here """

    base_url = AUTH_URL

    @authentication.authorization_required
    def get(self):
        auth = self.global_get('custom_auth')
        auth.invalidate_token(auth.get_token())
        return self.empty_response()


class Tokens(EndpointResource):
    """ List all active tokens for a user """

    base_url = AUTH_URL
    endkey = "token_id"
    endtype = "string"

    @authentication.authorization_required(roles=[config.ROLE_ADMIN])
    def get(self, token_id=None):
        auth = self.global_get('custom_auth')
        tokens = auth.get_tokens(user=auth._user)
        if token_id is None:
            return tokens

        for token in tokens:
            if token["id"] == token_id:
                return token

        errorMessage = "This token has not emitted to your account " + \
                       "or does not exist"
        return self.send_errors(
            "Token not found", errorMessage, code=hcodes.HTTP_BAD_NOTFOUND)

    @authentication.authorization_required
    def delete(self, token_id=None):
        """
            For additional security, tokens are invalidated both
            by chanding the user UUID and by removing single tokens
        """
        auth = self.global_get('custom_auth')
        user = self.get_current_user()
        tokens = auth.get_tokens(user=user)
        invalidated = False

        for token in tokens:
            # all or specific
            if token_id is None or token["id"] == token_id:
                done = auth.invalidate_token(token=token["token"], user=user)
                if not done:
                    return self.send_errors("Failed", "token: '%s'" % token)
                else:
                    logger.debug("Invalidated %s" % token['id'])
                    invalidated = True

        # Check

        # ALL
        if token_id is None:
            auth.invalidate_all_tokens(user=user)
        # SPECIFIC
        else:
            if not invalidated:
                message = "Not emitted for your account or does not exist"
                return self.send_errors(
                    "Token not found", message, code=hcodes.HTTP_BAD_NOTFOUND)

        return self.empty_response()


class AdminTokens(EndpointResource):
    """ Admin operations on token list """

    base_url = AUTH_URL
    endkey = "token_id"
    endtype = "string"

    @authentication.authorization_required(roles=[config.ROLE_ADMIN])
    def get(self, token_id):
        logger.critical("This endpoint should be restricted to admin only!")
        auth = self.global_get('custom_auth')
        token = auth.get_tokens(token_jti=token_id)
        if len(token) == 0:
            return self.send_errors(
                "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)
        return token

    @authentication.authorization_required(roles=[config.ROLE_ADMIN])
    def delete(self, token_id):
        logger.critical("This endpoint should be restricted to admin only!")
        auth = self.global_get('custom_auth')
        if not auth.destroy_token(token_id):
            return self.send_errors(
                "Token not found", token_id, code=hcodes.HTTP_BAD_NOTFOUND)

        return self.empty_response()


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

    # task = celery_app.AsyncResult(queue_id)
    # logger.critical(task.status)

    # if task.failed():
    #     output = task.get()
    #     return self.force_response(
    #         "THIS TASK IS FAILED!!! %s" % output,
    #         code=hcodes.HTTP_SERVER_ERROR)

    # if task.successful():
    #     output = task.get()
    #     # Forget about (and possibly remove the result of) this task.
    #     """
    #     The task back to the pending status, because:

    #     Task is waiting for execution or unknown.
    #     Any task id that is not known is implied
    #     to be in the pending state.
    #     """
    #     task.forget()

    #     return self.force_response(
    #         "THIS TASK IS COMPLETE. Output is: %s" % output,
    #         code=hcodes.HTTP_OK_CREATED)

    # if task.status == "SENT":
    #     return self.force_response(
    #         "THIS TASK IS STILL PENDING",
    #         code=hcodes.HTTP_OK_BASIC)

    # if task.status == "PROGRESS":
    #     current = task.info['current']
    #     total = task.info['total']

    #     perc = 100 * current / total

    #     return self.force_response(
    #         "THIS TASK IS RUNNING (%s %s)" % (perc, '%'),
    #         code=hcodes.HTTP_OK_BASIC)

    # return self.force_response(
    #     "This task does not exist",
    #     code=hcodes.HTTP_BAD_NOTFOUND)
