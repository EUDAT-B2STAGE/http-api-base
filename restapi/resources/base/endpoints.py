# -*- coding: utf-8 -*-

"""
Base endpoints: authorization, status, checks.
And a Farm: How to create endpoints into REST service.
"""

from __future__ import absolute_import

import re
import pytz
from datetime import datetime, timedelta
from restapi.resources import decorators as decorate

from flask import jsonify, current_app
from ..rest.definition import EndpointResource
from ..services.detect import CELERY_AVAILABLE
from ..services.authentication import BaseAuthentication
from restapi.resources.exceptions import RestApiException
from commons import htmlcodes as hcodes
from commons.globals import mem
from commons.logs import get_logger

import pyotp
import pyqrcode
# import hashlib
import base64
from io import BytesIO

log = get_logger(__name__)

REGISTER_FAILED_LOGIN = True
FORCE_FIRST_PASSWORD_CHANGE = True
MAX_PASSWORD_VALIDITY = 90  # 0
# DISABLE_UNUSED_CREDENTIALS_AFTER = 0
DISABLE_UNUSED_CREDENTIALS_AFTER = 180
MAX_LOGIN_ATTEMPTS = 3  # 0
# SECOND_FACTOR_AUTHENTICATION = None
TOTP = 'TOTP'
SECOND_FACTOR_AUTHENTICATION = TOTP
VERIFY_PASSWORD_STRENGHT = True

PROJECT_NAME = "Genomic Repository"
# FORCE_FIRST_PASSWORD_CHANGE = False
# SECOND_FACTOR_AUTHENTICATION = None
# MAX_PASSWORD_VALIDITY = 0


class HandleSecurity(object):

    def get_secret(self, user):
        # TO FIX: use a real secret
        # hashes does not works... maybe too long??
        # secret = hashlib.sha224(user.email.encode('utf-8'))
        # return secret.hexdigest()
        # same problem with str(user.uuid)

        # neither email works (problems with the @ character?)

        # decoding errors...
        # return str(user.name)

        return base64.b32encode(user.name.encode('utf-8'))

    def verify_token(self, auth, username, token):
        if token is None:

            if REGISTER_FAILED_LOGIN:
                auth.register_failed_login(username)
            msg = 'Invalid username or password'
            code = hcodes.HTTP_BAD_UNAUTHORIZED
            raise RestApiException(msg, status_code=code)

    def verify_totp(self, auth, user, totp_code):

        valid = True

        if totp_code is None:
            valid = False
        else:
            secret = self.get_secret(user)
            log.critical(secret)
            totp = pyotp.TOTP(secret)
            if not totp.verify(totp_code):
                if REGISTER_FAILED_LOGIN:
                    auth.register_failed_login(user.email)
                valid = False

        if not valid:
            msg = 'Invalid verification code'
            code = hcodes.HTTP_BAD_UNAUTHORIZED
            raise RestApiException(msg, status_code=code)

        return True

    def get_qrcode(self, user):

        secret = self.get_secret(user)
        log.critical(secret)
        totp = pyotp.TOTP(secret)

        otpauth_url = totp.provisioning_uri(PROJECT_NAME)
        qr_url = pyqrcode.create(otpauth_url)
        qr_stream = BytesIO()
        qr_url.svg(qr_stream, scale=5)
        return qr_stream.getvalue()

    # TO FIX: check password strength, if required
    def verify_password_strength(self, pwd, old_pwd):

        if pwd == old_pwd:
            return False, "Password cannot match the previous password"
        if len(pwd) < 8:
            return False, "Password is too short, use at least 8 characters"

        if not re.search("[a-z]", pwd):
            return False, "Password is too simple, missing lower case letters"
        if not re.search("[A-Z]", pwd):
            return False, "Password is too simple, missing upper case letters"
        if not re.search("[0-9]", pwd):
            return False, "Password is too simple, missing numbers"

        # special_characters = "['\s!#$%&\"(),*+,-./:;<=>?@[\\]^_`{|}~']"
        special_characters = "[^a-zA-Z0-9]"
        if not re.search(special_characters, pwd):
            return False, "Password is too simple, missing special characters"

        return True, None

    def change_password(self, auth, user,
                        password, new_password, password_confirm):

        if new_password != password_confirm:
            msg = "Your password doesn't match the confirmation"
            raise RestApiException(msg, status_code=hcodes.HTTP_BAD_CONFLICT)

        if VERIFY_PASSWORD_STRENGHT:
            check, msg = self.verify_password_strength(
                new_password, password)

            if not check:
                raise RestApiException(
                    msg, status_code=hcodes.HTTP_BAD_CONFLICT)

        if new_password is not None and password_confirm is not None:
            now = datetime.now(pytz.utc)
            user.password = BaseAuthentication.hash_password(new_password)
            user.last_password_change = now
            user.save()

            tokens = auth.get_tokens(user=user)
            for token in tokens:
                auth.invalidate_token(token=token["token"])
            # changes the user uuid invalidating all tokens
            auth.invalidate_all_tokens()

        return True

    def verify_blocked_username(self, auth, username):

        if not REGISTER_FAILED_LOGIN:
            # We do not register failed login
            pass
        elif MAX_LOGIN_ATTEMPTS <= 0:
            # We register failed login, but we do not put a max num of failures
            pass
            # TO FIX: implement get_failed_login
        elif auth.get_failed_login(username) < MAX_LOGIN_ATTEMPTS:
            # We register and put a max, but user does not reached it yet
            pass
        else:
            # Dear user, you have exceeded the limit
            msg = """
                Sorry, this account is temporarily blocked due to
                more than %d failed login attempts. Try again later"""\
                % MAX_LOGIN_ATTEMPTS
            code = hcodes.HTTP_BAD_UNAUTHORIZED
            raise RestApiException(msg, status_code=code)

    def verify_blocked_user(self, user):

        if DISABLE_UNUSED_CREDENTIALS_AFTER > 0:
            last_login = user.last_login
            now = datetime.now(pytz.utc)
            code = hcodes.HTTP_BAD_UNAUTHORIZED
            if last_login is not None:

                inactivity = timedelta(days=DISABLE_UNUSED_CREDENTIALS_AFTER)
                valid_until = last_login + inactivity

                if valid_until < now:
                    msg = "Sorry, this account is blocked for inactivity"
                    raise RestApiException(msg, status_code=code)


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

    @decorate.catch_error(exception=RestApiException, catch_generic=True)
    def post(self):

        # ########## INIT ##########
        security = HandleSecurity()

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

        totp_authentication = (
            SECOND_FACTOR_AUTHENTICATION is not None and
            SECOND_FACTOR_AUTHENTICATION == TOTP
        )

        if totp_authentication:
            totp_code = jargs.get('totp_code')
        else:
            totp_code = None
        # ##################################################
        # Now credentials are checked at every request
        if username is None or password is None:
            msg = "Missing username or password"
            raise RestApiException(
                msg, status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

        # auth instance from the global namespace
        auth = self.global_get('custom_auth')

        # ##################################################
        # Authentication control
        security.verify_blocked_username(auth, username)

        token, jti = auth.make_login(username, password)

        security.verify_token(auth, username, token)

        user = auth.get_user()

        security.verify_blocked_user(user)

        if totp_authentication and totp_code is not None:
            security.verify_totp(auth, user, totp_code)

        # ##################################################
        # If requested, change the password
        if new_password is not None and password_confirm is not None:

            pwd_changed = security.change_password(
                auth, user, password, new_password, password_confirm)

            if pwd_changed:
                password = new_password
                token, jti = auth.make_login(username, password)

        # ##################################################
        # Something is missing in the authentication, asking action to user
        message_body = {}
        message_body['actions'] = []
        error_message = None

        if totp_authentication and totp_code is None:
            message_body['actions'].append(SECOND_FACTOR_AUTHENTICATION)
            error_message = "You do not provided a valid second factor"

        epoch = datetime.fromtimestamp(0, pytz.utc)
        last_pwd_change = user.last_password_change
        if last_pwd_change is None or last_pwd_change == 0:
            last_pwd_change = epoch

        if FORCE_FIRST_PASSWORD_CHANGE and last_pwd_change == epoch:

            message_body['actions'].append('FIRST LOGIN')
            error_message = """
                Please change your temporary password
                """

            if totp_authentication:

                qr_code = security.get_qrcode(user)

                message_body["qr_code"] = qr_code

        elif MAX_PASSWORD_VALIDITY > 0:

            if last_pwd_change == epoch:
                expired = True
            else:
                valid_until = \
                    last_pwd_change + timedelta(days=MAX_PASSWORD_VALIDITY)
                expired = (valid_until < now)

            if expired:

                message_body['actions'].append('PASSWORD EXPIRED')
                error_message = "Your password is expired, please change it"

        if error_message is not None:
            return self.force_response(
                message_body,
                errors=error_message,
                code=hcodes.HTTP_BAD_FORBIDDEN)

        # ##################################################
        # Everything is ok, let's save authentication information

        if user.first_login is None:
            user.first_login = now
        user.last_login = now
        # Should be saved inside save_token...
        # user.save()
        auth.save_token(auth._user, token, jti)

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

        auth = self.global_get('custom_auth')
        # roles = []
        roles = {}
        for role in current_user.roles:
            # roles.append(role.name)
            roles[role.name] = role.name
        data["roles"] = roles
        data["isAdmin"] = auth.verify_admin()

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

        if SECOND_FACTOR_AUTHENTICATION is not None:
            data['2fa'] = SECOND_FACTOR_AUTHENTICATION

        return data

    @decorate.catch_error(exception=RestApiException, catch_generic=True)
    def put(self):
        """ Update profile for current user """

        auth = self.global_get('custom_auth')
        user = auth.get_user()
        username = user.email
        # if user.uuid != uuid:
        #     msg = "Invalid uuid: not matching current user"
        #     raise RestApiException(msg)

        data = self.get_input()
        password = data.get('password')
        new_password = data.get('new_password')
        password_confirm = data.get('password_confirm')
        totp_authentication = (
            SECOND_FACTOR_AUTHENTICATION is not None and
            SECOND_FACTOR_AUTHENTICATION == TOTP
        )
        if totp_authentication:
            totp_code = data.get('totp_code')
        else:
            totp_code = None

        security = HandleSecurity()

        if new_password is None or password_confirm is None:
            msg = "New password is missing"
            raise RestApiException(msg, status_code=hcodes.HTTP_BAD_REQUEST)

        if totp_authentication:
            security.verify_totp(auth, user, totp_code)
        else:
            token, jti = auth.make_login(username, password)
            security.verify_token(auth, username, token)

        security.change_password(
            auth, user, password, new_password, password_confirm)
        # I really don't why this save is required... since it is already
        # in change_password ... But if I remove it the new pwd is not saved...
        user.save()

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
