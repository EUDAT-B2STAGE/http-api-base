# -*- coding: utf-8 -*-

"""

### iRODS abstraction for FS virtualization with resources ###

My irods client class wrapper.

Since python3 is not ready for irods official client,
we based this wrapper on plumbum package handling shell commands.

"""

import os
import inspect
import re
import pytz
import dateutil.parser
from datetime import datetime, timedelta
from functools import lru_cache
from collections import OrderedDict
from rapydo.basher import BashCommands
from rapydo.exceptions import RestApiException
from rapydo.services.detect import IRODS_ENV, IRODS_EXTERNAL
from rapydo.services import ServiceFarm
from rapydo.confs import CUSTOM_PACKAGE
from rapydo.utils.certificates import Certificates
from rapydo.utils.meta import Meta
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

IRODS_USER_ALIAS = 'clientUserName'
CERTIFICATES_DIR = Certificates._dir

IRODS_DEFAULT_USER = 'guest'
IRODS_DEFAULT_ADMIN = os.environ.get('IRODS_DEFAULT_ADMIN_USER', 'rodsminer')

if not IRODS_EXTERNAL:
    IRODS_DEFAULT_USER = os.environ.get('RODSERVER_ENV_GSI_USER')
    IRODS_DEFAULT_ADMIN = os.environ.get('RODSERVER_ENV_GSI_ADMIN')


class IrodsException(RestApiException):

    def __init__(self, exception):
        super(IrodsException).__init__()
        self.parsedError = self.parseIrodsError(exception)

    def __str__(self):
        return self.parsedError

    def parse_CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME(
            self, utility, error_string, error_code, error_label, role='user'):
        # imeta add -d obj key value
        # imeta add -d obj key value
        # ERROR: rcModAVUMetadata failed with error -809000
        # CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME

        return "A resource already exists with this name"

    def parse_CAT_INVALID_USER(
            self, utility, error_string, error_code, error_label, role='user'):
        return "The requested user does not exist on the server"

    def parse_CAT_NO_ACCESS_PERMISSION(
            self, utility, error_string, error_code, error_label, role='user'):
        return "Permission denied"

    def parse_OVERWRITE_WITHOUT_FORCE_FLAG(
            self, utility, error_string, error_code, error_label, role='user'):
        return "Trying to overwrite existing object. " \
            + "You must set the force parameter to 'true'."

    def parse_USER_INPUT_PATH_ERR(
            self, utility, error_string, error_code, error_label, role='user'):
        return "The requested object does not exist on the specified path"

    def parse_CAT_NAME_EXISTS_AS_DATAOBJ(
            self, utility, error_string, error_code, error_label, role='user'):
        return "Directory requested already exist as a file/object"

    def parse_CAT_UNKNOWN_COLLECTION(
            self, utility, error_string, error_code, error_label, role='user'):
        return "The requested collection does not exist"

    def parse_SYS_INVALID_INPUT_PARAM(
            self, utility, error_string, error_code, error_label, role='user'):
        return "One input parameters is invalid (resource, file, etc.)"

    def parse_SYS_LINK_CNT_EXCEEDED_ERR(
            self, utility, error_string, error_code, error_label, role='user'):
        return "This collection is a mount point, cannot delete it"

    def parse_SYS_RESC_DOES_NOT_EXIST(
            self, utility, error_string, error_code, error_label, role='user'):
        return "Provided resource does not exist"

    def parse_SAME_SRC_DEST_PATHS_ERR(
            self, utility, error_string, error_code, error_label, role='user'):
        return "Destination and source having the same name"

    def parseIrodsError(self, error):
        error = str(error)
        log.debug("*%s*" % error)
# // TO FIX:
# this gets called twice

        # Error example:
        # ERROR: mkdirUtil: mkColl of /abs/path/to/resource error.
        # status = -809000 CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
        regExpr = "ERROR: (.+): (.+) status = (-[0-9]+) ([A-Z0-9_]+)"
        m = re.search(regExpr, error)
        if m:

            # es: mkdirUtil
            utility = m.group(1)

            # es: mkColl of /abs/path/to/resource error
            error_string = m.group(2)

            # es: -809000
            error_code = int(m.group(3))

            # es: CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
            error_label = m.group(4)

            method_name = 'parse_%s' % error_label
            method = getattr(self, method_name, None)
            if method is not None:
                return method(utility, error_string, error_code, error_label)

            return error_label

        # Error example:
        # ERROR: lsUtil: srcPath /abs/path/to/resource
        # does not exist or user lacks access permission
        regExpr = "^ERROR: (.*): (.*)$"
        m = re.search(regExpr, error)
        if m:
            # es: lsUtil
            utility = m.group(1)

            # es: srcPath /abs/path/to/resource
            # does not exist or user lacks access permission
            error_string = m.group(2)

            return error_string

        # Error example:
        # ERROR: rcModAccessControl failure  status = -827000 CAT_INVALID_USER
        regExpr = "ERROR: (.+) status = (-[0-9]+) ([A-Z0-9_]+)"
        m = re.search(regExpr, error)
        if m:
            utility = None
            error_string = m.group(1)
            error_code = int(m.group(2))
            error_label = m.group(3)

            method_name = 'parse_%s' % error_label
            method = getattr(self, method_name, None)
            if method is not None:
                return method(utility, error_string, error_code, error_label)

            return error_label

        return error


# ######################################
#
# # Basic iRODS client commands
#
# ######################################

class ICommands(BashCommands):
    """ iRODS icommands in a python wrapper class """

    _init_data = {}
    _current_environment = None
    _base_dir = ''

    first_resource = 'myResc'
    second_resource = 'replicaResc'

    def __init__(self, user=None, proxy=False, become_admin=False):

        # Recover plumbum shell enviroment
        super(ICommands, self).__init__()
        self._current_user = None

        if become_admin or user is None:
            self.become_admin()
            self.list()
        else:
            # Common use case: a request from another user
            self.change_user(user, proxy=proxy)

    def become_admin(self, user=None):
        if IRODS_EXTERNAL:
            raise ValueError("Cannot raise privileges in external service")
        return self.change_user(IRODS_DEFAULT_ADMIN)

    def get_resources_admin(self):
        resources = []
        out = self.admin(command='lr')
        if isinstance(out, str):
            resources = out.strip().split('\n')
        return resources

    def get_default_resource_admin(self, skip=['bundleResc']):
# // TO FIX:
# find out the right way to get the default irods resource
# note: we could use ienv
        resources = self.get_resources_admin()
        if len(resources) > 0:
            # Remove strange resources
            for element in skip:
                if element in resources:
                    resources.pop(resources.index(element))
            return list(resources)[::-1].pop()
        return None

    def get_user_home(self, user=None):

        if user is None:
            user = self.get_current_user()
# // TO FIX:
# don't we have an irods command for this?
        return os.path.join(
            self.get_current_zone(prepend_slash=True), 'home', user)

    def get_current_zone(self, prepend_slash=False):
# note: we could also use ienv (as admin?)
        userdata = self.get_user_info()
        zone = userdata['zone']
        if prepend_slash:
            zone = '/' + zone
        return zone

    def handle_collection_path(self, ipath):
        """
            iRODS specific pattern to handle paths
        """

        home = self.get_base_dir()

        # Should add the base dir if doesn't start with /
        if ipath is None or ipath == '':
            ipath = home
        elif ipath[0] != '/':
            ipath = home + '/' + ipath
        else:
            current_zone = self.get_current_zone()
            if not ipath.startswith('/' + current_zone):
                # Add the zone
                ipath = '/' + current_zone + ipath

        # Append / if missing in the end
        if ipath[-1] != '/':
            ipath += '/'

        return ipath

    def get_irods_path(self, collection, filename=None):

        path = self.handle_collection_path(collection)
        if filename is not None:
            path += filename
        return path

    def check_certificate_validity(self, certfile, validity_interval=1):
        args = ["x509", "-in", certfile, "-text"]
        output = self.execute_command("openssl", args)

        pattern = re.compile(
            r"Validity.*\n\s*Not Before: (.*)\n" +
            r"\s*Not After *: (.*)")
        validity = pattern.search(output).groups()

        not_before = dateutil.parser.parse(validity[0])
        not_after = dateutil.parser.parse(validity[1])
        now = datetime.now(pytz.utc) - timedelta(hours=validity_interval)

        valid = (not_after > now) and (not_before < now)

        return valid, not_before, not_after

    def prepare_irods_environment(self, user, schema='GSI', proxy=False):
        """
        Prepare the OS variables environment
        which allows to become another user using the GSI protocol.

        It requires that user to be recognized inside the iRODS server,
        e.g. the certificate is available on the server side.
        """

        irods_env = os.environ.copy()

        zone = os.environ.get('IRODS_ZONE', None)
        if zone is None:
            raise BaseException(
                "Missing zone: Use env var 'IRODS_ZONE'")
        home = os.environ.get('IRODS_CUSTOM_HOME', '/home')

        irods_env['IRODS_USER_NAME'] = user
        irods_env['IRODS_HOME'] = '/' + zone + home + '/' + user
        irods_env['IRODS_AUTHENTICATION_SCHEME'] = schema
        irods_env['IRODS_HOST'] = os.environ['ICAT_1_ENV_IRODS_HOST']
        irods_env['IRODS_PORT'] = \
            int(os.environ['ICAT_1_PORT'].split(':')[::-1][0])
        irods_env['IRODS_ZONE'] = zone

        if schema == 'GSI':

# could be fixed changing the dir rodsminer inside the docker image...
            if user == 'rods':
                user = 'rodsminer'

            # ## X509 certificates variables
            # CA Authority
            irods_env['X509_CERT_DIR'] = CERTIFICATES_DIR + '/caauth'

            ###############################
            # PROXY CERTIFICATE (EUDAT)
            if proxy:
                irods_env['X509_USER_PROXY'] = \
                    CERTIFICATES_DIR + '/' + user + '/userproxy.crt'
            ###############################
            # USER PEMs: Private (key) and Public (Cert)
            elif os.path.isdir(CERTIFICATES_DIR + '/' + user):
                log.debug("Using standard x509 certificates (user %s)" % user)

                certfile = CERTIFICATES_DIR + '/' + user + '/usercert.pem'
                keyfile = CERTIFICATES_DIR + '/' + user + '/userkey.pem'
                irods_env['X509_USER_CERT'] = certfile
                irods_env['X509_USER_KEY'] = keyfile

                valid, not_before, not_after = \
                    self.check_certificate_validity(certfile)

                if not valid:
                    # log.critical(user)
                    # log.critical(certfile)
                    # log.critical(not_before)
                    # log.critical(not_after)
                    # log.critical(valid)
                    raise IrodsException(
                        "Invalid GSI certificate (%s). Validity: %s - %s"
                        % (user, not_before, not_after)
                    )
            ###############################
            # PROXY CERTIFICATE (myproxy)
            # NOTE: this is way too long, it should be splitted in subfunctions
            else:
                log.debug("Using proxy certificates (user %s)" % user)
                proxy_cert_file = CERTIFICATES_DIR + '/' + user + '.pem'

                if not os.path.isfile(proxy_cert_file):
                    # Proxy file does not exist
                    valid = False
                else:
                    # Proxy exists, verify validity
                    # args = ["x509", "-in", proxy_cert_file, "-text"]
                    # output = self.execute_command("openssl", args)

                    # pattern = re.compile(
                    #     r"Validity.*\n\s*Not Before: (.*)\n" +
                    #     r"\s*Not After *: (.*)")
                    # validity = pattern.search(output).groups()

                    # # not_before = dateutil.parser.parse(validity[0])
                    # not_after = dateutil.parser.parse(validity[1])
                    # # NOW - 1 hour
                    # now = datetime.now(pytz.utc) - timedelta(hours=1)

                    # valid = not_after > now

                    valid, not_before, not_after = \
                        self.check_certificate_validity(proxy_cert_file)

                ##################
                # Proxy file does not exist or expired
                if not valid:
                    log.warning("Invalid proxy for %s refresh" % user)
                    try:

                        parameters = {}
                        parameters["user"] = user
                        parameters["proxy_cert_file"] = proxy_cert_file
                        parameters["env"] = irods_env

                        # TO FIX: move get_proxy_certificate in rapydo.utils
                        meta = Meta()
                        module_path = \
                            "%s.resources.proxy_certificates" % CUSTOM_PACKAGE
                        module = meta.get_module_from_string(module_path)
                        valid = module.get_proxy_certificate(**parameters)

                        if valid:
                            log.info(
                                "Proxy refreshed for %s" % user)
                        else:
                            log.error(
                                "Cannot refresh proxy for user %s" % user)
                    except Exception as e:
                        log.critical(
                            "Cannot refresh proxy for user %s" % user)
                        log.critical(e)

                ##################
                if valid:
                    irods_env['X509_USER_CERT'] = proxy_cert_file
                    irods_env['X509_USER_KEY'] = proxy_cert_file
                else:
                    log.critical("Cannot find a valid certificate file")

        if schema == 'PAM':
            # irodsSSLCACertificateFile PATH/TO/chain.pem
            # irodsSSLVerifyServer      cert
            log.critical("PAM not IMPLEMENTED yet")
            return False

        # if user == IRODS_DEFAULT_ADMIN:
        #     for key, value in irods_env.items():
        #         if key.startswith('IRODS_') or key.startswith('X509'):
        #             print("export", key + '="' + str(value) + '"')

        self._current_environment = irods_env
        return irods_env

    def change_user(self, user=None, proxy=False):
        """ Impersonification of another user because you're an admin """

# Where to change with:
# https://github.com/EUDAT-B2STAGE/http-api/issues/1#issuecomment-196729596
        self._current_environment = None

        if user is None:
            # Do not change user, go with the main admin
            user = self._init_data['irods_user_name']
        else:
            #########
            # # OLD: impersonification because i am an admin
            # Use an environment variable to reach the goal
            # os.environ[IRODS_USER_ALIAS] = user

            #########
            # # NEW: use the certificate
            self.prepare_irods_environment(user, proxy=proxy)

        self._current_user = user
        log.verbose("Switched to user '%s'" % user)
        # clean lru_cache because we changed user
        self.get_user_info.cache_clear()

        # If i want to check
        # return self.list(self.get_user_home(user))
        return True

    def get_default_user(self):
        return IRODS_DEFAULT_USER

    def get_current_user(self):
        userdata = self.get_user_info()
        return userdata['name']

    @staticmethod
    def get_translated_user(self, user):
        """
## // TO BE DEPRECATED
        """
        from rapydo.services.irods.translations import \
            importAccountsToIrodsUsers
        return AccountsToIrodsUsers.email2iuser(user)

    def translate_graph_user(self, graph, graph_user):
        from rapydo.services.irods.translations import Irods2Graph
        return Irods2Graph(graph, self).graphuser2irodsuser(graph_user)

    ###################
    # Basic command with the GSI plugin
    def basic_icom(self, com, args=[]):
        """
        Use the current environment variables to be another irods user
        """
        try:
            return self.execute_command(
                com,
                parameters=args,
                env=self._current_environment,
                parseException=True,
                raisedException=IrodsException
            )
        except IrodsException as e:

            irods_exception = IrodsException(e)
            raise irods_exception

    ###################
    # ICOMs !!!
    def list_resources(self):
        com = 'ilsresc'
        iout = self.basic_icom(com).strip()
        log.debug("Resources %s" % iout)
        return iout.split("\n")

    def get_base_resource(self):
        resources = self.list_resources()
        if len(resources) > 0:
            return resources[0]
        return None

    def get_base_dir(self):
        com = "ipwd"
        iout = self.basic_icom(com).strip()
        log.very_verbose("Base dir is %s" % iout)
        return iout

    # def go_home(self):
    #     """
    #     For debugging/testing certificates
    #     """
    #     com = "icd"
    #     return self.basic_icom(com).strip()

    def create_empty(self, path, directory=False, ignore_existing=False):
        args = [path]
        if directory:
            com = "imkdir"
            if ignore_existing:
                args.append("-p")
        else:
            # // TODO:
            # super call of create_tempy with file (touch)
            # icp / iput of that file
            # super call of remove for the original temporary file
            log.warning("NOT IMPLEMENTED for a file '%s'" %
                           inspect.currentframe().f_code.co_name)
            return

        # This command does not give you any output
        self.basic_icom(com, args)
        log.debug("Created %s" % path)

        return self.handle_collection_path(path)

    def list(self, path=None, recursive=False, detailed=False, acl=False):
        """ List the files inside an iRODS path/collection """

        # Prepare the command
        com = "ils"
        if path is None:
            path = self.get_base_dir()
        args = [path]
        if detailed:
            args.append("-l")
        if recursive:
            args.append("-r")
        if acl:
            args.append("-A")
        # Do it
        stdout = self.basic_icom(com, args)
        # Parse output
        lines = stdout.splitlines()
        replicas = []
        for line in lines:
            replicas.append(re.split("\s+", line.strip()))
        return replicas

    def copy(self, sourcepath, destpath,
             recursive=False, force=False,
             compute_checksum=False, compute_and_verify_checksum=False):
        com = 'icp'
        args = []

        if force:
            args.append('-f')
        if recursive:
            args.append('-r')

        # Checksum
        if compute_and_verify_checksum:
            args.append('-K')
        elif compute_checksum:
            args.append('-k')

        # Normal parameters
        args.append(sourcepath)
        args.append(destpath)

        # Execute
        self.basic_icom(com, args)
        # Debug
        log.debug("Copyied file: %s -> %s" % (sourcepath, destpath))

    def remove(self, path, recursive=False, force=False, resource=None):
        com = 'irm'
        args = []
        if force:
            args.append('-f')

        if resource is not None:
            com = 'itrim'
            args = ['-S', resource]

        if recursive:
            args.append('-r')

        args.append(path)

        # Execute
        self.basic_icom(com, args)
        # Debug
        log.debug("Removed irods object: %s" % path)

    def open(self, absolute_path, destination):
        com = 'iget'
        args = [absolute_path]
        args.append(destination)
        # Execute
        iout = self.basic_icom(com, args)
        # Debug
        log.debug("Obtaining irods object: %s" % absolute_path)
        return iout

    def save(self, path, destination=None, force=False, resource=None):
        com = 'iput'
        args = [path]
        if force:
            args.append('-f')
        if destination is not None:
            args.append(destination)

        # Bug fix: currently irods does not use the default resource anymore?
        if resource is None:
            resource = self.get_base_resource()
        args.append('-R')
        args.append(resource)

        # Execute
        return self.basic_icom(com, args)

    def get_collection_from_path(self, absolute_path):
        return os.path.dirname(absolute_path)

    def get_absolute_path(self, *args, root=None):
        if len(args) < 1:
            return root
        if root is None and not args[0].startswith('/'):
            root = '/'
        return os.path.join(root, *args)

    def move(self, absolute_path, destination):
        com = 'imv'
        args = [absolute_path]
        args.append(destination)
        # Execute
        iout = self.basic_icom(com, args)
        # Debug
        log.debug("Obtaining irods object: %s" % absolute_path)
        return iout

    def admin(self, command, user=None, extra=None):
        """
        Admin commands to manage users and stuff like that.
        Note: it will give irods errors if current user has not privileges.
        """

        com = 'iadmin'
        args = [command]
        if user is not None:
            args.append(user)
        if extra is not None:
            args.append(extra)
        log.debug("iRODS admininistration command '%s'" % command)
        return self.basic_icom(com, args)

    def admin_list(self):
        """
        How to explore collections in a debug way
        """
        return self.admin('ls')

    def create_user(self, user, admin=False):

        if user is None:
            log.error("Asking for NULL user...")
            return False

        user_type = 'rodsuser'
        if admin:
            user_type = 'rodsadmin'

        try:
            self.admin('mkuser', user, user_type)
            return True
        except IrodsException as e:
            if 'CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME' in str(e):
                log.warning("User %s already exists in iRODS" % user)
                return False
            raise e

    def set_inheritance(self, path, inheritance=True, recursive=False):
        com = 'ichmod'
        args = []

        if recursive:
            args.append('-r')

        if inheritance:
            args.append("inherit")
        else:
            args.append("noinherit")

        args.append(path)
        # Execute
        self.basic_icom(com, args)
        # Debug
        log.debug("Set inheritance %r to %s" % (inheritance, path))

    def set_permissions(self, path, permission, userOrGroup, recursive=False):
        com = 'ichmod'
        args = []
        if recursive:
            args.append('-r')

        # To be verified, 'permission' should be null/read/write/own
        args.append(permission)
        args.append(userOrGroup)
        args.append(path)
        # Execute
        self.basic_icom(com, args)
        # Debug
        log.debug("Set %s permission to %s for %s" %
                     (permission, path, userOrGroup))

    def get_resources_from_file(self, filepath):
        output = self.list(path=filepath, detailed=True)
        resources = []
        for elements in output:
            # elements = line.split()
            if len(elements) < 3:
                continue
            resources.append(elements[2])

        log.debug("%s: found resources %s" % (filepath, resources))
        return resources

    def get_permissions(self, path):
        """
            Output example:
            {
                'path': '/your_zone/your_path/',
                'ACL': [
                            ['your_user', 'your_zone', 'own'],
                            ['other_user', 'your_zone', 'read']
                        ],
                'inheritance': 'Disabled'
            }
        """
        iout = self.list(path=path, acl=True)

        data = {}
        for d in iout:
            if d[0] == "C-":
                data["path"] = d[1]
            elif d[0] == "ACL":
                data["ACL"] = d[2:]
            elif d[0] == "Inheritance":
                data["inheritance"] = d[2]
            else:
                data["path"] = d[0]

        popMe = None
        for index, element in enumerate(data["ACL"]):

            if element == 'object':
                popMe = index
            else:
                data["ACL"][index] = re.split('#|:', data["ACL"][index])

        if popMe is not None:
            data["ACL"].pop(popMe)

        return data

# // TO FIX:
    def get_current_user_environment(self):
        com = 'ienv'
        output = self.basic_icom(com)
        print("ENV IS", output)
        return output

    def setInDict(self, dataDict, mapList, value):
        for k in mapList[:-1]:
            if k not in dataDict:
                dataDict[k] = {}
            dataDict = dataDict[k]
        dataDict[mapList[-1]] = value

    def get_list_as_json(self, root):

        data = {}

        if root is None:
            root = ''

        iout = self.list(path=root, detailed=True, recursive=True)
        path = None
        pathLen = 0
        rootLen = len(root)
        acl = None
        inheritance = None

        path_prefix = None
        for d in iout:

            if len(d) <= 1:
                if path is None:
                    path = d[0]
                    if path.endswith(":"):
                        path = path[:-1]
                    if not path.endswith("/"):
                        path += "/"

                    pathLen = len(path)

                path_prefix = d[0][pathLen:-1]
                continue

            # Unable to retrieve a path for this collection
            # This collection may be empty
            if path is None:
                continue

            if d[0] == "ACL":
                acl = d
                continue

            if d[0] == "Inheritance":
                inheritance = d
                continue

            row = {}

            keys = []
            if d[0] == "C-":

                absname = d[1]

                name = absname[pathLen:]
                keys = name.split("/")

                row["name"] = name
                row["owner"] = "-"
                row["acl"] = acl
                row["acl_inheritance"] = inheritance
                row["object_type"] = "collection"
                row["content_length"] = 0
                row["last_modified"] = 0
                row["objects"] = {}
                start = 0
                if rootLen > 0:
                    start = 1 + rootLen
                row["path"] = path[start:]

            else:

                name = d[6]

                if path_prefix is None or path_prefix == '':
                    keys = [name]
                else:
                    keys = path_prefix.split("/")
                    keys.append(name)

                row["name"] = name
                row["owner"] = d[0]
                row["acl"] = acl
                row["acl_inheritance"] = inheritance
                row["object_type"] = "dataobject"
                row["content_length"] = d[3]
                row["last_modified"] = d[4]
                start = 0
                if rootLen > 0:
                    start = 1 + rootLen
                row["path"] = path[start:]

            if len(keys) == 1:
                self.setInDict(data, keys, row)
            else:
                new_keys = []
                for index, k in enumerate(keys):
                    new_keys.append(k)
                    if index < len(keys) - 1:
                        new_keys.append('objects')

                self.setInDict(data, new_keys, row)

        return data

    def list_as_json(self, root, level=0, recursive=True, firstRoot=None):

        data = {}

        if root is None:
            root = ''

        if firstRoot is None:
            firstRoot = root

        iout = self.list(path=root, detailed=True)
        path = None
        pathLen = 0
        rootLen = len(firstRoot)
        acl = None
        inheritance = None
        for d in iout:

            if len(d) <= 1:
                if path is None:
                    path = d[0]
                    if path.endswith(":"):
                        path = path[:-1]
                    if not path.endswith("/"):
                        path += "/"

                    pathLen = len(path)
                continue

            # Unable to retrieve a path for this collection
            # This collection may be empty
            if path is None:
                continue

            row = {}

            if d[0] == "ACL":
                acl = d
                continue
            if d[0] == "Inheritance":
                inheritance = d
                continue

            if d[0] == "C-":

                absname = d[1]
                if recursive:
                    objects = self.list_as_json(
                        absname, level + 1, True, firstRoot)

                name = absname[pathLen:]
                # print(path, "vs", name)

                row["name"] = name
                row["owner"] = "-"
                row["acl"] = acl
                row["acl_inheritance"] = inheritance
                row["object_type"] = "collection"
                row["content_length"] = 0
                row["last_modified"] = 0
                if recursive:
                    row["objects"] = objects
                start = 0
                if rootLen > 0:
                    start = 1 + rootLen
                row["path"] = path[start:]

            else:

                row["name"] = d[6]
                row["owner"] = d[0]
                row["acl"] = acl
                row["acl_inheritance"] = inheritance
                row["object_type"] = "dataobject"
                row["content_length"] = d[3]
                row["last_modified"] = d[4]
                start = 0
                if rootLen > 0:
                    start = 1 + rootLen
                row["path"] = path[start:]

            data[row["name"]] = row

        return data

    @lru_cache(maxsize=4)
    def get_user_info(self, username=None):
## // TO FIX:
# should we cache this method?
        com = 'iuserinfo'
        args = []
        if username is not None:
            args.append(username)
        output = self.basic_icom(com, args)

        if username is not None:
            reg_exp = "User %s does not exist\." % username
            if re.search(reg_exp, output):
                return None

        # parse if info is about current user
        data = {}
        groups = []
        reg_exp = r"([^\s]+)\s*:\s+([^\s]+)\n"
        for key, value in re.findall(reg_exp, output):
            if key == 'group':
                groups.append(value)
            else:
                data[key] = value
        data['groups'] = groups
        # from beeprint import pp
        # pp(data)
        return data

    def user_has_group(self, username, groupname):
        info = self.get_user_info(username)
        if info is None:
            return False
        if 'groups' not in info:
            return False
        return groupname in info['groups']

    def check_user_exists(self, username, checkGroup=None):
        userdata = self.get_user_info(username)
        if userdata is None:
            return False, "User %s does not exist" % username
        if checkGroup not in userdata['groups']:
            return False, "User %s is not in group %s" % (username, checkGroup)
        return True, "OK"

    def current_location(self, ifile):
        """
        irods://130.186.13.14:1247/cinecaDMPZone/home/pdonorio/replica/test2
        """
        protocol = 'irods'
        URL = "%s://%s:%s%s" % (
            protocol,
            self._current_environment['IRODS_HOST'],
            self._current_environment['IRODS_PORT'],
            os.path.join(self._base_dir, ifile))
        return URL

    def get_resource_from_dataobject(self, ifile):
        """ The attribute of resource from a data object """
        details = self.list(ifile, True)
        resources = []
        for element in details:
            # 2nd position is the resource in irods ils -l
            resources.append(element[2])
        return resources

    def is_collection(self, path):

        """
        iRods check if collection or data object:
        ils -A path
        if first line ends with ':' it's a collection
        """

        try:
            lines = self.list(path, recursive=False, detailed=False, acl=True)
        # Skip error 'element does not exist'
        except IrodsException as e:
            # Note: ils does not distinguish between
            # permission denied or object non existing...
            if "does not exist" not in str(e):
                raise e
            else:
                return False

        if len(lines) < 0:
            raise KeyError("Unexpected empty response from irods listing")
        first_lines = lines[::-1].pop()
        # print(first_lines)

        if first_lines.pop().endswith(':'):
            log.debug("Collection: %s" % path)
            return True
        return False

    def query_icat(self, query, key):
        com = 'iquest'
        args = ["%s" % query]
        output = self.basic_icom(com, args)
        log.debug("%s query: [%s]\n%s" % (com, query, output))
        if 'CAT_NO_ROWS_FOUND' in output:
            return None
        return output.split('\n')[0].lstrip("%s = " % key)

    def query_user(self, select="USER_NAME", where="USER_NAME", field=None):
        query = "SELECT %s WHERE %s = '%s'" % (select, where, field)
        return self.query_icat(query, select)

    def get_user_from_dn(self, dn):
        return self.query_user(where='USER_DN', field=dn)

    def user_exists(self, user):
        return self.query_user(field=user) == user

################################################
################################################
##  NEED TO CHECK ALL OF THIS ICOMMANDS BELOW
################################################
################################################

    # def check(self, path, retcodes=(0, 4)):
    #     """
    #     Retcodes for this particular case, skip also error 4, no file found
    #     """
    #     (status, stdin, stdout) = self.list(path, False, retcodes)
    #     log.debug("Check %s with %s " % (path, status))
    #     return status == 0

    def search(self, path, like=True):
        com = "ilocate"
        if like:
            path += '%'
        log.debug("iRODS search for %s" % path)
        # Execute
        out = self.execute_command(com, path)
        content = out.strip().split('\n')
        print("TEST", content)
        return content

    def replica(self, dataobj, replicas_num=1, resOri=None, resDest=None):
        """ Replica
        Replicate a file in iRODS to another storage resource.
        Note that replication is always within a zone.
        """

        com = "irepl"
        if resOri is None:
            resOri = self.first_resource
        if resDest is None:
            resDest = self.second_resource

        args = [dataobj]
        args.append("-P")  # debug copy
        args.append("-n")
        args.append(replicas_num)
        # Ori
        args.append("-S")
        args.append(resOri)
        # Dest
        args.append("-R")
        args.append(resDest)

        return self.basic_icom(com, args)

    def replica_list(self, dataobj):
        return self.get_resource_from_dataobject(dataobj)


# ######################################
#
# # iRODS and METADATA
#
# ######################################

class IMetaCommands(ICommands):

    """ irods icommands in a class """

    ###################
    # METADATA for irods

    def meta_sys_list(self, path):
        """ Listing file system metadata """
        com = "isysmeta"
        args = ['ls']
        args.append(path)
        out = self.basic_icom(com, args)
        metas = {}
        if out:
            # print("OUTPUT IS", out)
            pattern = re.compile("([a-z_]+):\s+([^\n]+)")
            metas = pattern.findall(out)
        return metas

#     def meta_command(self, path, action='list', attributes=[], values=[]):
#         com = "imeta"
#         args = []

#         # Base commands for imeta:
#         # ls, set, rm
#         # - see https://docs.irods.org/master/icommands/metadata/#imeta
#         if action == "list":
#             args.append("ls")
#         elif action == "write":
#             args.append("set")
#         elif action != "":
#             raise KeyError("Unknown action for metadata: " + action)
#         # imeta set -d FILEPATH a b
#         # imeta ls -d FILEPATH
#         # imeta ls -d FILEPATH a

#         # File to list metadata?
#         args.append("-d") # if working with data object metadata
#         args.append(path)

#         if len(attributes) > 0:
#             if len(values) == 0 or len(attributes) == len(values):
#                 for key in range(0,len(attributes)):
#                     args.append(attributes[key])
#                     try:
#                         args.append(values[key])
#                     except:
#                         pass
#             else:
#                 log.debug("No valid attributes specified for action %s" % action)
#                 log.debug("Attrib %s Val %s" % (attributes, values) )

#         # Execute
#         return self.execute_command(com, args)

#     def meta_list(self, path, attributes=[]):
#         """ Listing all irods metadata """
#         out = self.meta_command(path, 'list', attributes)

#         # Parse out
#         metas = {}
#         pattern = re.compile("attribute:\s+(.+)")
#         keys = pattern.findall(out)
#         pattern = re.compile("value:\s+(.+)")
#         values = pattern.findall(out)
#         for j in range(0, len(keys)):
#             metas[keys[j]] = values[j]

#         # m1 = re.search(r"attribute:\s+(.+)", out)
#         # m2 = re.search(r"value:\s+(.+)", out)
#         # if m1 and m2:
#         #     metas[m1.group(1)] = m2.group(1)

#         return metas

#     def meta_write(self, path, attributes, values):
#         return self.meta_command(path, 'write', attributes, values)


# ######################################
#
# # Execute iRules
#
# ######################################

# class IRuled(IMetaCommands):

#     ###################
#     # IRULES and templates
#     def irule_execution(self, rule=None, rule_file=None):
#         com='irule'
#         args=[]
#         if rule is not None:
#             args.append(rule)
#             log.info("Executing irule %s" % rule)
#         elif rule_file is not None:
#             args.append('-F')
#             args.append(rule_file)
#             log.debug("Irule execution from file %s" % rule_file)

#         # Execute
#         return self.execute_command(com, args)

#     def irule_from_file(self, rule_file):
#         return self.irule_execution(None, rule_file)

# ######################################
#
# # EUDAT project irods configuration
#
# ######################################

# class EudatICommands(IRuled):
#     """ See project documentation
#     http://eudat.eu/User%20Documentation%20-%20iRODS%20Deployment.html
#     """

#     latest_pid = None

#     def search(self, path, like=True):
#         """ Remove eudat possible metadata from this method """
#         ifiles = super(EudatICommands, self).search(path, like)
#         for ifile in ifiles:
#             if '.metadata/' in ifile:
#                 log.debug("Skipping metadata file %s" % ifile)
#                 ifiles.remove(ifile)
#         return ifiles

#     def execute_rule_from_template(self, rule, context={}):
#         """
#         Using my template class for executing an irods rule
#         from a rendered file with variables in context
#         """
#         jin = Templa(rule)
#         # Use jinja2 templating
#         irule_file = jin.template2file(context)
#         # Call irule from template rendered
#         out = self.irule_from_file(irule_file)
#         # Remove file
#         os.remove(irule_file)
#         # Send response back
#         return out

#     def parse_rest_json(self, json_string=None, json_file=None):
#         """ Parsing REST API output in JSON format """
#         import json
#         json_data = ""

#         if json_string is not None:
#             json_data = json.loads(json_string)
#         elif json_file is not None:
#             with open(json_file) as f:
#                 json_data = json.load(f)

#         metas = {}
#         for meta in json_data:
#             key = meta['type']
#             value = meta['parsed_data']
#             metas[key] = value

#         return metas

#     # PID
#     def register_pid(self, dataobj):
#         """ Eudat rule for irods to register a PID to a Handle """

#         # Path fix
#         dataobj = os.path.join(self._base_dir, dataobj)

#         if appconfig.mocking():

#             #pid = "842/a72976e0-5177-11e5-b479-fa163e62896a"
#             # 8 - 4 - 4 - 4 - 12
#             base = "842"
#             code = string_generator(8)
#             code += "-" + str(random.randint(1000,9999))
#             code += "-" + string_generator(4) + "-" + string_generator(4)
#             code += "-" + string_generator(12)
#             pid = base + "/" + code

#         else:
#             context = {
#                 'irods_file': dataobj.center(len(dataobj)+2, '"')
#             }
#             pid = self.execute_rule_from_template('getpid', context)

#         return pid

#     def meta_list(self, path, attributes=[]):
#         """
#         Little trick to save PID from metadata listing:
#         override the original method
#         """
#         metas = super(EudatICommands, self).meta_list(path, attributes)
#         if 'PID' in metas:
#             self.latest_pid = metas['PID']
#         else:
#             self.latest_pid = None
#         return metas

#     # PID
#     def check_pid(self, dataobj):
#         """ Should get this value from irods metadata """

#         # Solved with a trick
#         pid = self.latest_pid
#         # Otherwise
#         #self.meta_list(dataobj, ['PID'])
#         # Might also use an irods rule to seek
#         #self.irule_from_file(irule_file)

#         return pid

#     def pid_metadata(self, pid):
#         """ Metadata derived only inside an Eudat enviroment """

#         # Binary included inside the neoicommands docker image
#         com = 'epicc'
#         credentials = './conf/credentials.json'
#         args = ['os', credentials, 'read', pid]

#         json_data = ""
#         select = {
#             'location':'URL',
#             'checksum': 'CHECKSUM',
#             'parent_pid':'EUDAT/PPID',
#         }
#         metas = {}

#         if appconfig.mocking():
# # // TO FIX:
#             empty = ""
# # Generate random
# # e.g. irods://130.186.13.14:1247/cinecaDMPZone/home/pdonorio/replica/test2
# # e.g. sha2:dCdRWFfS2TGm/4BfKQPu1WdQSdBwxRoxCRMX3zan3SM=
# # e.g. 842/52ae4c2c-4feb-11e5-afd1-fa163e62896a
#             pid_metas = {
#                 'URL': empty,
#                 'CHECKSUM': empty,
#                 'EUDAT/PPID': empty,
#             }
# # // TO REMOVE:
#             # Fake, always the same
#             metas = self.parse_rest_json(None, './tests/epic.pid.out')

#         else:
#             log.debug("Epic client for %s " % args)
#             json_data = self.execute_command(com, args).strip()
#             if json_data.strip() == 'None':
#                 return {}

#             # Get all epic metas
#             metas = self.parse_rest_json(json_data)

#         ## Meaningfull data
#         pid_metas = {}
#         for name, selection in select.items():
#             value = None
#             if selection in metas:
#                 value = metas[selection]
#             pid_metas[name] = value

#         return pid_metas

#     def eudat_replica(self, dataobj_ori, dataobj_dest=None, pid_register=True):
#         """ Replication as Eudat B2safe """

#         if dataobj_dest is None:
#             dataobj_dest = dataobj_ori + ".replica"
#         dataobj_ori = os.path.join(self._base_dir, dataobj_ori)
#         dataobj_dest = os.path.join(self._base_dir, dataobj_dest)

#         context = {
#             'dataobj_source': dataobj_ori.center(len(dataobj_ori)+2, '"'),
#             'dataobj_dest': dataobj_dest.center(len(dataobj_dest)+2, '"'),
#             'pid_register': \
#                 str(pid_register).lower().center(len(str(pid_register))+2, '"'),
#         }

#         return self.execute_rule_from_template('replica', context)

#     def eudat_find_ppid(self, dataobj):
#         log.debug("***REPLICA EUDAT LIST NOT IMPLEMENTED YET ***")
#         exit()


class IrodsFarm(ServiceFarm):

    @staticmethod
    def define_service_name():
        return 'irods'

    def init_connection(self, app):
        self.get_instance()
        log.verbose("iRODS seems online")

    @classmethod
    def get_instance(cls, user=None, proxy=False, become_admin=False):

        # Default or Admin
        if user is None:
            if 'IRODS_USER' in os.environ:
                user = os.environ.get('IRODS_USER')
            else:
                if IRODS_EXTERNAL:
                    raise KeyError("No iRODS user available")
                else:
                    log.warning("Becoming iRODS admin")

# We should check if here classmethod is the wrong option
        # cls._irods = IMetaCommands(user)
        # return cls._irods

        return IMetaCommands(user, proxy=proxy, become_admin=become_admin)
