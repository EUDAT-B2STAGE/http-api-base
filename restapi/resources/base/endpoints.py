# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import

from flask import jsonify, current_app
from ..rest.definition import EndpointResource
from ..services.detect import CELERY_AVAILABLE
from ..services.authentication import BaseAuthentication
from commons import htmlcodes as hcodes
from commons.globals import mem
from commons.logs import get_logger

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

        # NOTE: swagger dictionary is read only once, at server init time
        swagjson = mem.customizer._definitions

        # NOTE: changing dinamically options, based on where the client lies
        from commons import get_api_url
        api_url, _ = get_api_url()
        scheme, host = api_url.rstrip('/').split('://')
        swagjson['host'] = host
        swagjson['schemes'] = [scheme]

        # Jsonify, so we skip custom response building
        return jsonify(swagjson)


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

    def get_user(self, auth):

        iamadmin = auth.verify_admin()

        if iamadmin:
            username = self.get_input(single_parameter='username')
            if username is not None:
                return auth.get_user_object(username=username)

        return self.get_current_user()

    def get(self, token_id=None):

        auth = self.global_get('custom_auth')
        user = self.get_user(auth)

        if user is None:
            return self.send_errors(
                "Invalid", "Bad username", code=hcodes.HTTP_BAD_REQUEST)

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

    def delete(self, token_id=None):
        """
            For additional security, tokens are invalidated both
            by chanding the user UUID and by removing single tokens
        """

        auth = self.global_get('custom_auth')
        user = self.get_user(auth)
        if user is None:
            return self.send_errors(
                "Invalid", "Bad username", code=hcodes.HTTP_BAD_REQUEST)

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


class Profile(EndpointResource):
    """ Current user informations """

    def get(self):

        # auth = self.global_get('custom_auth')
        current_user = self.get_current_user()
        data = {
            'uuid': current_user.uuid,
            'status': "Valid user",
            'email': current_user.email
        }

        # roles = []
        roles = {}
        for role in current_user.roles:
            # roles.append(role.name)
            roles[role.name] = role.name
        data["roles"] = roles
        data["isAdmin"] = "admin_root" in roles

        if hasattr(current_user, 'name'):
            data["name"] = current_user.name

        if hasattr(current_user, 'surname'):
            data["surname"] = current_user.surname

        if hasattr(current_user, 'irods_user'):
            data["irods_user"] = current_user.irods_user
            if not data["irods_user"]:
                data["irods_user"] = None
            elif data["irods_user"] == '':
                data["irods_user"] = None
            elif data["irods_user"] == '0':
                data["irods_user"] = None
            elif data["irods_user"][0] == '-':
                data["irods_user"] = None

        return data

    def put(self, uuid):
        # TO FIX: this should be a POST method...

        """ Create or update profile for current user """

        from flask_restful import request
        try:
            user = self.get_current_user()
            if user.uuid != uuid:
                return self.send_errors(
                    "Invalid uuid",
                    "Identifier specified does not match current user",
                )

            data = request.get_json(force=True)

            key = "newpassword"
            if key not in data:
                return self.send_errors(
                    "Invalid request", "Missing %s value" % key,
                    code=hcodes.HTTP_BAD_REQUEST
                )
            user.password = BaseAuthentication.hash_password(data[key])
            user.save()

            auth = self.global_get('custom_auth')
            tokens = auth.get_tokens(user=auth._user)
            for token in tokens:
                # for graphdb it just remove the edge
                auth.invalidate_token(token=token["token"])
            # changes the user uuid invalidating all tokens
            auth.invalidate_all_tokens()

        except:
            return self.send_errors(
                "Error", "Unknown error, please contact administrators",
                code=hcodes.HTTP_BAD_REQUEST
            )

        return self.empty_response()


class Internal(EndpointResource):
    """ Token and Role authentication test """

    def get(self):
        return "I am internal"


class Admin(EndpointResource):
    """ Token and Role authentication test """

    def get(self):
        return "I am admin!"


# In case you have celery queue,
# you get a queue endpoint for free
if CELERY_AVAILABLE:
    from commons.services.celery import celery_app

    class Queue(EndpointResource):

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

        def put(self, task_id):
            celery_app.control.revoke(task_id)
            return self.empty_response()

        def delete(self, task_id):
            celery_app.control.revoke(task_id, terminate=True)
            return self.empty_response()
