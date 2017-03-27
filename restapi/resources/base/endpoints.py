# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import

import pytz
from datetime import datetime, timedelta

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

    def login_failed(self, auth, username, message):

        REGISTER_FAILED_LOGIN = True

        if REGISTER_FAILED_LOGIN:
            auth.register_failed_login(username)

        return self.send_errors(
            message=message,
            code=hcodes.HTTP_BAD_UNAUTHORIZED
        )

    def check_password_strength(self, pwd, old_pwd):

        if pwd == old_pwd:
            return False, "Password cannot match the previous password"
        if len(pwd) < 8:
            return False, "Password too short"

        return True, None

    def post(self):

        # NOTE: In case you need different behaviour when using unittest
        # if current_app.config['TESTING']:
        #     print("\nThis is inside a TEST\n")

        REGISTER_FAILED_LOGIN = True
        FORCE_FIRST_PASSWORD_CHANGE = True
        MAX_PASSWORD_VALIDITY = 90  # 0
        # DISABLE_UNUSED_CREDENTIALS_AFTER = 0
        DISABLE_UNUSED_CREDENTIALS_AFTER = 180
        MAX_LOGIN_ATTEMPTS = 3  # 0
        # SECOND_FACTOR_AUTHENTICATION = None
        TOTP = 'TOTP'
        SECOND_FACTOR_AUTHENTICATION = TOTP
        CHECK_PASSWORD_STRENGHT = True

        unauthorized = hcodes.HTTP_BAD_UNAUTHORIZED
        forbidden = hcodes.HTTP_BAD_FORBIDDEN
        conflict = hcodes.HTTP_BAD_CONFLICT

        now = datetime.now(pytz.utc)

        jargs = self.get_input()
        username = jargs.get('username')
        if username is None:
            username = jargs.get('email')

        password = jargs.get('password')
        if password is None:
            password = jargs.get('pwd')

        new_password = jargs.get('new_password')
        password_confirm = jargs.get('password_confirm')
        totp_code = jargs.get('totp_code')

        # NOTE: now is checked at every request
        if username is None or password is None:
            return self.send_errors(
                message="Missing username or password",
                code=unauthorized)

        # auth instance from the global namespace
        auth = self.global_get('custom_auth')

        if REGISTER_FAILED_LOGIN and MAX_LOGIN_ATTEMPTS > 0:
            # TO FIX: implement get_failed_login
            if auth.get_failed_login(username) >= MAX_LOGIN_ATTEMPTS:
                msg = """
                    Sorry, this account is temporarily blocked due to
                    more than %d failed login attempts. Try again later"""\
                    % MAX_LOGIN_ATTEMPTS
                return self.send_errors(message=msg, code=unauthorized)

        token, jti = auth.make_login(username, password)
        if token is None:
            return self.login_failed(
                auth, username, 'Invalid username or password')

        user = auth.get_user()

        if DISABLE_UNUSED_CREDENTIALS_AFTER > 0:
            last_login = user.last_login
            if last_login is not None and last_login > 0:

                inactivity = timedelta(days=DISABLE_UNUSED_CREDENTIALS_AFTER)
                valid_until = last_login + inactivity

                if valid_until < now:
                    msg = "Sorry, this account is blocked for inactivity"
                    return self.send_errors(message=msg, code=unauthorized)

        message_body = {}
        message_body['actions'] = []
        error_message = None

        if totp_code is not None:
            import pyotp

            # TO FIX: use a real secret based on user.SomeThing
            totp = pyotp.TOTP('base32secret3232')
            if not totp.verify(totp_code):

                return self.login_failed(auth, username, 'Invalid code')

        if new_password is not None and password_confirm is not None:
            if new_password != password_confirm:
                msg = "Your password doesn't match the confirmation"
                return self.send_errors(message=msg, code=conflict)

            if CHECK_PASSWORD_STRENGHT:
                check, msg = self.check_password_strength(
                    new_password, password)

                if not check:
                    return self.send_errors(message=msg, code=conflict)

            # TO FIX: check password strength, if required

        if new_password is not None and password_confirm is not None:
            user.password = BaseAuthentication.hash_password(new_password)
            user.last_password_change = now
            user.save()

            password = new_password

        if SECOND_FACTOR_AUTHENTICATION is not None:

            if totp_code is not None:
                # should be already validated
                pass
            else:
                message_body['actions'].append(SECOND_FACTOR_AUTHENTICATION)
                error_message = "You do not provided a valid second factor"

        last_pwd_change = user.last_password_change
        if last_pwd_change is None:
            last_pwd_change = 0
        if FORCE_FIRST_PASSWORD_CHANGE and last_pwd_change == 0:

            message_body['actions'].append('FIRST LOGIN')
            error_message = "This is your first login"

            if SECOND_FACTOR_AUTHENTICATION is not None and \
               SECOND_FACTOR_AUTHENTICATION == TOTP:

                import pyotp
                import pyqrcode
                from io import BytesIO

                totp = pyotp.TOTP('base32secret3232')

                otpauth_url = totp.provisioning_uri("GenomicRepository")
                qr_url = pyqrcode.create(otpauth_url)
                qr_stream = BytesIO()
                qr_url.svg(qr_stream, scale=5)

                message_body["qr_code"] = qr_stream.getvalue()

        elif MAX_PASSWORD_VALIDITY > 0:
            valid_until = \
                last_pwd_change + timedelta(days=MAX_PASSWORD_VALIDITY)

            if valid_until < now:

                message_body['actions'].append('PASSWORD EXPIRED')
                error_message = "This password is expired"

        if error_message is not None:
            # temp_token, temp_jti = auth.create_temporary_token(user)
            # auth.save_token(auth._user, temp_token, temp_jti)
            return self.force_response(
                # {'token': temp_token, 'actions': actions},
                message_body,
                errors=error_message,
                code=forbidden)

        auth.save_token(auth._user, token, jti)
        if user.first_login is None:
            user.first_login = now
        user.last_login = now
        user.save()
        # TO FIX: split response as above in access_token and token_type?
        # # The right response should be the following
        # {
        #   "scope": "https://b2stage.cineca.it/api/.*",
        #   "access_token": "EEwJ6tF9x5WCIZDYzyZGaz6Khbw7raYRIBV_WxVvgmsG",
        #   "token_type": "Bearer",
        #   "user": "pippo",
        #   "expires_in": 28800
        # }
        # TO FIX: also set headers in a standard way if it exists

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
                message="Invalid: bad username", code=hcodes.HTTP_BAD_REQUEST)

        tokens = auth.get_tokens(user=user)

        if token_id is None:
            return tokens

        for token in tokens:
            if token["id"] == token_id:
                return token

        errorMessage = """Either this token was not emitted for your account
                          or it does not exist"""
        return self.send_errors(
            message=errorMessage, code=hcodes.HTTP_BAD_NOTFOUND)

    def delete(self, token_id=None):
        """
            For additional security, tokens are invalidated both
            by chanding the user UUID and by removing single tokens
        """

        auth = self.global_get('custom_auth')
        user = self.get_user(auth)
        if user is None:
            return self.send_errors(
                message="Invalid: bad username", code=hcodes.HTTP_BAD_REQUEST)

        tokens = auth.get_tokens(user=user)
        invalidated = False

        for token in tokens:
            # all or specific
            if token_id is None or token["id"] == token_id:
                done = auth.invalidate_token(token=token["token"], user=user)
                if not done:
                    return self.send_errors(message="Failed '%s'" % token)
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
                message = "Token not found: " + \
                    "not emitted for your account or does not exist"
                return self.send_errors(
                    message=message, code=hcodes.HTTP_BAD_NOTFOUND)

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
                    message="Invalid uuid: not matching current user",
                )

            data = request.get_json(force=True)

            key = "newpassword"
            if key not in data:
                return self.send_errors(
                    message="Invalid request: missing %s value" % key,
                    code=hcodes.HTTP_BAD_REQUEST
                )
            user.password = BaseAuthentication.hash_password(data[key])
            user.last_password_change = datetime.now(pytz.utc)
            user.save()

            auth = self.global_get('custom_auth')
            tokens = auth.get_tokens(user=auth._user)
            for token in tokens:
                # for graphdb it just remove the edge
                auth.invalidate_token(token=token["token"])
            # changes the user uuid invalidating all tokens
            auth.invalidate_all_tokens()

        except BaseException:
            return self.send_errors(
                message="Unknown error, please contact administrators",
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

            if active_tasks is None:
                active_tasks = []
            if revoked_tasks is None:
                revoked_tasks = []
            if scheduled_tasks is None:
                scheduled_tasks = []

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
