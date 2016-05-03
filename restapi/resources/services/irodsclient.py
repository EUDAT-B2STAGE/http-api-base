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
from collections import OrderedDict
from ..basher import BashCommands
from confs.config import IRODS_ENV

# from ..templating import Templa
# from . import string_generator, appconfig

from restapi import get_logger
logger = get_logger(__name__)

IRODS_USER_ALIAS = 'clientUserName'
CERTIFICATES_DIR = '/opt/certificates'

class IrodsException(Exception):
    pass


# ######################################
#
# # Basic iRODS client commands
#
# ######################################


class ICommands(BashCommands):
    """irods icommands in a class"""

    _init_data = {}
    _current_environment = None
    _base_dir = ''

    first_resource = 'demoResc'
    second_resource = 'replicaResc'

    def __init__(self, user=None, irodsenv=IRODS_ENV):

        # Recover plumbum shell enviroment
        super(ICommands, self).__init__()

        # How to add a new user
        # $ iadmin mkuser guest rodsuser

        # In case i am the admin
        if user is None:
            # Use the physical file for the irods environment
            self.irodsenv = irodsenv
            self.become_admin()
            # Verify if connected
# // TO FIX: change it to ilsresc
            self.list()
        # A much common use case: a request from another user
        else:
            self.change_user(user)

    #######################
    # ABOUT CONFIGURATION
    def become_admin(self):
        """
        Try to check if you're on Docker and have variables set
        to become iRODS administrator.

        It can also be used without docker by setting the same
        environment variables.

        Possible schemes: 'credentials', 'GSI', 'PAM'
        """
        authscheme = os.environ.get('IRODS_AUTHSCHEME', 'credentials')

        user = os.environ.get('IRODS_USER', None)
        if user is None:
            raise BaseException(
                "Cannot become admin without env var 'IRODS_USER' set!")

        if authscheme == 'credentials' or authscheme == 'PAM':

# // TO FIX: use the method prepare_irods_environment...

            self._init_data = OrderedDict({
                "irods_host": os.environ['ICAT_1_ENV_IRODS_HOST'],
                "irods_port":
                    int(os.environ['ICAT_1_PORT'].split(':')[::-1][0]),
                "irods_user_name": user,
                "irods_zone_name": os.environ['IRODS_ZONE'],
                # "irods_password": os.environ['ICAT_1_ENV_IRODS_PASS']
            })

            # Set external auth scheme if requested
            if authscheme is not 'credentials':
                self._init_data["irods_authentication_scheme"] = authscheme

            with open(self.irodsenv, 'w') as fw:
                import json
                json.dump(self._init_data, fw)

            self.set_password()
            logger.info("Saved irods admin credentials")
            logger.debug("iRODS admin environment found\n%s" % self._init_data)

        elif authscheme == 'GSI':
            self.prepare_irods_environment(user, authscheme)

    def set_password(self, tmpfile='/tmp/temppw'):
        """
        Interact with iinit to set the password.
        This is the case i am not using certificates.
        """

        passw = os.environ.get('ICAT_1_ENV_IRODS_PASS', None)
        if passw is None:
            raise BaseException(
                "Missing password: Use env var 'ICAT_1_ENV_IRODS_PASS'")

        from plumbum.cmd import iinit
        with open(tmpfile, 'w') as fw:
            fw.write(passw)
        com = iinit < tmpfile
        com()
        os.remove(tmpfile)
        logger.debug("Pushed credentials")

    def get_user_home(self, user):
        return os.path.join(
            '/' + self._init_data['irods_zone_name'],
            'home',
            user)

    def prepare_irods_environment(self, user, schema='GSI'):
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
            # ## X509 certificates variables
            # CA Authority
            irods_env['X509_CERT_DIR'] = CERTIFICATES_DIR + '/caauth'
            # ## USER PEMs: Private (key) and Public (Cert)
            irods_env['X509_USER_CERT'] = \
                CERTIFICATES_DIR + '/' + user + '/usercert.pem'
            irods_env['X509_USER_KEY'] = \
                CERTIFICATES_DIR + '/' + user + '/userkey.pem'

            # PROXY ?

        # # DEBUG
        # for key, item in irods_env.items():
        #     if 'irods' == key[0:5].lower() or 'x509_' == key[0:5].lower():
        #         print("ITEM", key, item)

        if schema == 'PAM':
            # irodsSSLCACertificateFile PATH/TO/chain.pem
            # irodsSSLVerifyServer      cert
            logger.critical("PAM not IMPLEMENTED yet")
            return False

        self._current_environment = irods_env
        return irods_env

    def change_user(self, user=None):
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
            self.prepare_irods_environment(user)

        logger.info("Switched to user '%s'" % user)

        # If i want to check
        # return self.list(self.get_user_home(user))
        return True

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

            parsedError = self.parseIrodsError(e);
            raise IrodsException(parsedError)


    def parseIrodsError(self, error):

        import re

        logger.debug(error)

        error = str(error)

        #Error example:
        #ERROR: mkdirUtil: mkColl of /abs/path/to/resource error. status = -809000 CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME
        regExpr = "^ERROR: (.*): (.*) status = (-[0-9]+) (.*)$"
        m = re.search(regExpr, error)
        if m is not None:

            #http://wiki.irods.org/index.php/iRODS_Error_Codes
            utility = m.group(1)            #es: mkdirUtil
            error_string = m.group(2)       #es: mkColl of /abs/path/to/resource error
            error_code = int(m.group(3))    #es: -809000
            error_label = m.group(4)        #es CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME

            # Human Readable error
            hr_error = error_label

            if   error_code == CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                hr_error = "A resource already exists with this name"
            elif error_code == CAT_NO_ACCESS_PERMISSION:
                hr_error = "Permission denied"

            return hr_error


        #Error example:
        #ERROR: lsUtil: srcPath /abs/path/to/resource does not exist or user lacks access permission
        regExpr = "^ERROR: (.*): (.*)$"
        m = re.search(regExpr, error)
        if m is not None:
            logger.debug(m)
            utility = m.group(1)        #es: lsUtil
            error_string = m.group(2)   #es: srcPath /abs/path/to/resource does not exist or user lacks access permission

            return error_string

        return error


    ###################
    # ICOMs !!!
    def get_base_dir(self):
        com = "ipwd"
        iout = self.basic_icom(com).strip()
        logger.debug("Base dir is %s" % iout)
        return iout

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
            logger.debug("NOT IMPLEMENTED for a file '%s'" %
                         inspect.currentframe().f_code.co_name)
            return

        # Debug
        self.basic_icom(com, args)
        logger.debug("Created %s" % path)

    def list(self, path=None, detailed=False, acl=False):
        """ List the files inside an iRODS path/collection """

        # Prepare the command
        com = "ils"
        if path is None:
            path = self.get_base_dir()
        args = [path]
        if detailed:
            args.append("-l")
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
        logger.debug("Copyied file: %s -> %s" % (sourcepath, destpath))

    def remove(self, path, recursive=False, force=False):
        com = 'irm'
        args = []
        if force:
            args.append('-f')
        if recursive:
            args.append('-r')
        args.append(path)
        # Execute
        self.basic_icom(com, args)
        # Debug
        logger.debug("Removed irods object: %s" % path)

    def open(self, absolute_path, destination):
        com = 'iget'
        args = [absolute_path]
        args.append(destination)
        # Execute
        iout = self.basic_icom(com, args)
        # Debug
        logger.debug("Obtaining irods object: %s" % absolute_path)
        return iout

    def save(self, path, destination=None):
        com = 'iput'
        args = [path]
        if destination is not None:
            args.append(destination)
        # Execute
        return self.basic_icom(com, args)

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
        logger.debug("Set inheritance %r to %s" % (inheritance, path))

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
        logger.debug("Set %s permission to %s for %s" % (permission, path, userOrGroup))

################################################
################################################

###### WE NEED TO CHECK ALL THIS ICOMMANDS BELOW

################################################
################################################

    def get_resource_from_dataobject(self, ifile):
        """ The attribute of resource from a data object """
        details = self.list(ifile, True)
        resources = []
        for element in details:
            # 2nd position is the resource in irods ils -l
            resources.append(element[2])
        return resources

    def current_location(self, ifile):
        """
        irods://130.186.13.14:1247/cinecaDMPZone/home/pdonorio/replica/test2
        """
        protocol = 'irods://'
        URL = protocol + \
            self._init_data['irodsHost'] + ':' + \
            self._init_data['irodsPort'] + \
            os.path.join(self._base_dir, ifile)
        return URL

    def check(self, path, retcodes=(0, 4)):
        """
        Retcodes for this particular case, skip also error 4, no file found
        """
        (status, stdin, stdout) = self.list(path, False, retcodes)
        logger.debug("Check %s with %s " % (path, status))
        return status == 0

    def search(self, path, like=True):
        com = "ilocate"
        if like:
            path += '%'
        logger.debug("iRODS search for %s" % path)
        # Execute
        try:
            out = self.execute_command(com, path)
        except Exception:
            logger.debug("No data found.")
            exit(1)
        if out:
            return out.strip().split('\n')
        return out

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

        return self.execute_command(com, args)

    def replica_list(self, dataobj):
        return self.get_resource_from_dataobject(dataobj)


# ######################################
#
# # iRODS and METADATA
#
# ######################################

# class IMetaCommands(ICommands):
#     """irods icommands in a class"""
#     ###################
#     # METADATA for irods

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
#                 logger.debug("No valid attributes specified for action %s" % action)
#                 logger.debug("Attrib %s Val %s" % (attributes, values) )

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

#     def meta_sys_list(self, path):
#         """ Listing file system metadata """
#         com = "isysmeta"
#         args = ['ls']
#         args.append(path)
#         out = self.execute_command(com, args)
#         metas = {}
#         if out:
#             pattern = re.compile("([a-z_]+):\s+([^\n]+)")
#             metas = pattern.findall(out)
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
#             logger.info("Executing irule %s" % rule)
#         elif rule_file is not None:
#             args.append('-F')
#             args.append(rule_file)
#             logger.debug("Irule execution from file %s" % rule_file)

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
#                 logger.debug("Skipping metadata file %s" % ifile)
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
#             logger.debug("Epic client for %s " % args)
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
#         logger.debug("***REPLICA EUDAT LIST NOT IMPLEMENTED YET ***")
#         exit()


#######################################
# Creating the iRODS main instance
test_irods = ICommands()
# Note: this will be changed in the near future
# We should create the instance before every request
# (see Flask before_request decorator)



#WHERE TO PUT THEM??

#######################################
# http://wiki.irods.org/index.php/iRODS_Error_Codes
#######################################


#System Type Codes 1000 - 2999000
SYS_SOCK_OPEN_ERR = -1000
SYS_SOCK_BIND_ERR = -2000
SYS_SOCK_ACCEPT_ERR = -3000
SYS_HEADER_READ_LEN_ERR = -4000
SYS_HEADER_WRITE_LEN_ERR = -5000
SYS_HEADER_TPYE_LEN_ERR = -6000
SYS_CAUGHT_SIGNAL = -7000
SYS_GETSTARTUP_PACK_ERR = -8000
SYS_EXCEED_CONNECT_CNT = -9000
SYS_USER_NOT_ALLOWED_TO_CONN = -10000
SYS_READ_MSG_BODY_INPUT_ERR = -11000
SYS_UNMATCHED_API_NUM = -12000
SYS_NO_API_PRIV = -13000
SYS_API_INPUT_ERR = -14000
SYS_PACK_INSTRUCT_FORMAT_ERR = -15000
SYS_MALLOC_ERR = -16000
SYS_GET_HOSTNAME_ERR = -17000
SYS_OUT_OF_FILE_DESC = -18000
SYS_FILE_DESC_OUT_OF_RANGE = -19000
SYS_UNRECOGNIZED_REMOTE_FLAG = -20000
SYS_INVALID_SERVER_HOST = -21000
SYS_SVR_TO_SVR_CONNECT_FAILED = -22000
SYS_BAD_FILE_DESCRIPTOR = -23000
SYS_INTERNAL_NULL_INPUT_ERR = -24000
SYS_CONFIG_FILE_ERR = -25000
SYS_INVALID_ZONE_NAME = -26000
SYS_COPY_LEN_ERR = -27000
SYS_PORT_COOKIE_ERR = -28000
SYS_KEY_VAL_TABLE_ERR = -29000
SYS_INVALID_RESC_TYPE = -30000
SYS_INVALID_FILE_PATH = -31000
SYS_INVALID_RESC_INPUT = -32000
SYS_INVALID_PORTAL_OPR = -33000
SYS_PARA_OPR_NO_SUPPORT = -34000
SYS_INVALID_OPR_TYPE = -35000
SYS_NO_PATH_PERMISSION = -36000
SYS_NO_ICAT_SERVER_ERR = -37000
SYS_AGENT_INIT_ERR = -38000
SYS_PROXYUSER_NO_PRIV = -39000
SYS_NO_DATA_OBJ_PERMISSION = -40000
SYS_DELETE_DISALLOWED = -41000
SYS_OPEN_REI_FILE_ERR = -42000
SYS_NO_RCAT_SERVER_ERR = -43000
SYS_UNMATCH_PACK_INSTRUCTI_NAME = -44000
SYS_SVR_TO_CLI_MSI_NO_EXIST = -45000
SYS_COPY_ALREADY_IN_RESC = -46000
SYS_RECONN_OPR_MISMATCH = -47000
SYS_INPUT_PERM_OUT_OF_RANGE = -48000
SYS_FORK_ERROR = -49000
SYS_PIPE_ERROR = -50000
SYS_EXEC_CMD_STATUS_SZ_ERROR = -51000
SYS_PATH_IS_NOT_A_FILE = -52000
SYS_UNMATCHED_SPEC_COLL_TYPE = -53000
SYS_TOO_MANY_QUERY_RESULT = -54000
SYS_SPEC_COLL_NOT_IN_CACHE = -55000
SYS_SPEC_COLL_OBJ_NOT_EXIST = -56000
SYS_REG_OBJ_IN_SPEC_COLL = -57000
SYS_DEST_SPEC_COLL_SUB_EXIST = -58000
SYS_SRC_DEST_SPEC_COLL_CONFLICT = -59000
SYS_UNKNOWN_SPEC_COLL_CLASS = -60000
SYS_DUPLICATE_XMSG_TICKET = -61000
SYS_UNMATCHED_XMSG_TICKET = -62000
SYS_NO_XMSG_FOR_MSG_NUMBER = -63000
SYS_COLLINFO_2_FORMAT_ERR = -64000
SYS_CACHE_STRUCT_FILE_RESC_ERR = -65000
SYS_NOT_SUPPORTED = -66000
SYS_TAR_STRUCT_FILE_EXTRACT_ERR = -67000
SYS_STRUCT_FILE_DESC_ERR = -68000
SYS_TAR_OPEN_ERR = -69000
SYS_TAR_EXTRACT_ALL_ERR = -70000
SYS_TAR_CLOSE_ERR = -71000
SYS_STRUCT_FILE_PATH_ERR = -72000
SYS_MOUNT_MOUNTED_COLL_ERR = -73000
SYS_COLL_NOT_MOUNTED_ERR = -74000
SYS_STRUCT_FILE_BUSY_ERR = -75000
SYS_STRUCT_FILE_INMOUNTED_COLL = -76000
SYS_COPY_NOT_EXIST_IN_RESC = -77000
SYS_RESC_DOES_NOT_EXIST = -78000
SYS_COLLECTION_NOT_EMPTY = -79000
SYS_OBJ_TYPE_NOT_STRUCT_FILE = -80000
SYS_WRONG_RESC_POLICY_FOR_BUN_OPR = -81000
SYS_DIR_IN_VAULT_NOT_EMPTY = -82000
SYS_OPR_FLAG_NOT_SUPPORT = -83000
SYS_TAR_APPEND_ERR = -84000
SYS_INVALID_PROTOCOL_TYPE = -85000
SYS_UDP_CONNECT_ERR = -86000
SYS_UDP_TRANSFER_ERR = -89000
SYS_UDP_NO_SUPPORT_ERR = -90000
SYS_READ_MSG_BODY_LEN_ERR = -91000
CROSS_ZONE_SOCK_CONNECT_ERR = -92000
SYS_NO_FREE_RE_THREAD = -93000
SYS_BAD_RE_THREAD_INX = -94000
SYS_CANT_DIRECTLY_ACC_COMPOUND_RESC = -95000
SYS_SRC_DEST_RESC_COMPOUND_TYPE = -96000
SYS_CACHE_RESC_NOT_ON_SAME_HOST = -97000
SYS_NO_CACHE_RESC_IN_GRP = -98000
SYS_UNMATCHED_RESC_IN_RESC_GRP = -99000
SYS_CANT_MV_BUNDLE_DATA_TO_TRASH = -100000
SYS_CANT_MV_BUNDLE_DATA_BY_COPY = -101000
SYS_EXEC_TAR_ERR = -102000
SYS_CANT_CHKSUM_COMP_RESC_DATA = -103000
SYS_CANT_CHKSUM_BUNDLED_DATA = -104000
SYS_RESC_IS_DOWN = -105000
SYS_UPDATE_REPL_INFO_ERR = -106000
SYS_COLL_LINK_PATH_ERR = -107000
SYS_LINK_CNT_EXCEEDED_ERR = -108000
SYS_CROSS_ZONE_MV_NOT_SUPPORTED = -109000
SYS_RESC_QUOTA_EXCEEDED = -110000

#User Input Errors 300000 - 499000
USER_AUTH_SCHEME_ERR = -300000
USER_AUTH_STRING_EMPTY = -301000
USER_RODS_HOST_EMPTY = -302000
USER_RODS_HOSTNAME_ERR = -303000
USER_SOCK_OPEN_ERR = -304000
USER_SOCK_CONNECT_ERR = -305000
USER_STRLEN_TOOLONG = -306000
USER_API_INPUT_ERR = -307000
USER_PACKSTRUCT_INPUT_ERR = -308000
USER_NO_SUPPORT_ERR = -309000
USER_FILE_DOES_NOT_EXIST = -310000
USER_FILE_TOO_LARGE = -311000
OVERWITE_WITHOUT_FORCE_FLAG = -312000
UNMATCHED_KEY_OR_INDEX = -313000
USER_CHKSUM_MISMATCH = -314000
USER_BAD_KEYWORD_ERR = -315000
USER__NULL_INPUT_ERR = -316000
USER_INPUT_PATH_ERR = -317000
USER_INPUT_OPTION_ERR = -318000
USER_INVALID_USERNAME_FORMAT = -319000
USER_DIRECT_RESC_INPUT_ERR = -320000
USER_NO_RESC_INPUT_ERR = -321000
USER_PARAM_LABEL_ERR = -322000
USER_PARAM_TYPE_ERR = -323000
BASE64_BUFFER_OVERFLOW = -324000
BASE64_INVALID_PACKET = -325000
USER_MSG_TYPE_NO_SUPPORT = -326000
USER_RSYNC_NO_MODE_INPUT_ERR = -337000
USER_OPTION_INPUT_ERR = -338000
SAME_SRC_DEST_PATHS_ERR = -339000
USER_RESTART_FILE_INPUT_ERR = -340000
RESTART_OPR_FAILED = -341000
BAD_EXEC_CMD_PATH = -342000
EXEC_CMD_OUTPUT_TOO_LARGE = -343000
EXEC_CMD_ERROR = -344000
BAD_INPUT_DESC_INDEX = -345000
USER_PATH_EXCEEDS_MAX = -346000
USER_SOCK_CONNECT_TIMEDOUT = -347000
USER_API_VERSION_MISMATCH = -348000
USER_INPUT_FORMAT_ERR = -349000
USER_ACCESS_DENIED = -350000
CANT_RM_MV_BUNDLE_TYPE = -351000
NO_MORE_RESULT = -352000
NO_KEY_WD_IN_MS_INP_STR = -353000
CANT_RM_NON_EMPTY_HOME_COLL = -354000
CANT_UNREG_IN_VAULT_FILE = -355000
NO_LOCAL_FILE_RSYNC_IN_MSI = -356000

#File Driver Errors 500000 - 800000
FILE_INDEX_LOOKUP_ERR = -500000
UNIX_FILE_OPEN_ERR = -510000
UNIX_FILE_CREATE_ERR = -511000
UNIX_FILE_READ_ERR = -512000
UNIX_FILE_WRITE_ERR = -513000
UNIX_FILE_CLOSE_ERR = -514000
UNIX_FILE_UNLINK_ERR = -515000
UNIX_FILE_STAT_ERR = -516000
UNIX_FILE_FSTAT_ERR = -517000
UNIX_FILE_LSEEK_ERR = -518000
UNIX_FILE_FSYNC_ERR = -519000
UNIX_FILE_MKDIR_ERR = -520000
UNIX_FILE_RMDIR_ERR = -521000
UNIX_FILE_OPENDIR_ERR = -522000
UNIX_FILE_CLOSEDIR_ERR = -523000
UNIX_FILE_READDIR_ERR = -524000
UNIX_FILE_STAGE_ERR = -525000
UNIX_FILE_GET_FS_FREESPACE_ERR = -526000
UNIX_FILE_CHMOD_ERR = -527000
UNIX_FILE_RENAME_ERR = -528000
UNIX_FILE_TRUNCATE_ERR = -529000
UNIX_FILE_LINK_ERR = -530000

#Universal MSS Driver Errors
UNIV_MSS_SYNCTOARCH_ERR = -550000
UNIV_MSS_STAGETOCACHE_ERR = -551000
UNIV_MSS_UNLINK_ERR = -552000
UNIV_MSS_MKDIR_ERR = -553000
UNIV_MSS_CHMOD_ERR = -554000
UNIV_MSS_STAT_ERR = -555000
HPSS_AUTH_NOT_SUPPORTED = -600000
HPSS_FILE_OPEN_ERR = -610000
HPSS_FILE_CREATE_ERR = -611000
HPSS_FILE_READ_ERR = -612000
HPSS_FILE_WRITE_ERR = -613000
HPSS_FILE_CLOSE_ERR = -614000
HPSS_FILE_UNLINK_ERR = -615000
HPSS_FILE_STAT_ERR = -616000
HPSS_FILE_FSTAT_ERR = -617000
HPSS_FILE_LSEEK_ERR = -618000
HPSS_FILE_FSYNC_ERR = -619000
HPSS_FILE_MKDIR_ERR = -620000
HPSS_FILE_RMDIR_ERR = -621000
HPSS_FILE_OPENDIR_ERR = -622000
HPSS_FILE_CLOSEDIR_ERR = -623000
HPSS_FILE_READDIR_ERR = -624000
HPSS_FILE_STAGE_ERR = -625000
HPSS_FILE_GET_FS_FREESPACE_ERR = -626000
HPSS_FILE_CHMOD_ERR = -627000
HPSS_FILE_RENAME_ERR = -628000
HPSS_FILE_TRUNCATE_ERR = -629000
HPSS_FILE_LINK_ERR = -630000
HPSS_AUTH_ERR  = -631000
HPSS_WRITE_LIST_ERR = -632000
HPSS_READ_LIST_ERR = -633000
HPSS_TRANSFER_ERR  = -634000
HPSS_MOVER_PROT_ERR = -635000

#Amazon S3 Errors
S3_INIT_ERROR = -701000
S3_PUT_ERROR = -702000
S3_GET_ERROR = -703000
S3_FILE_UNLINK_ERR = -715000
S3_FILE_STAT_ERR = -716000
S3_FILE_COPY_ERR = -717000

#Catalog Library Errors 800000 - 880000
CATALOG_NOT_CONNECTED = -801000
CAT_ENV_ERR        = -802000
CAT_CONNECT_ERR    = -803000
CAT_DISCONNECT_ERR = -804000
CAT_CLOSE_ENV_ERR  = -805000
CAT_SQL_ERR        = -806000
CAT_GET_ROW_ERR    = -807000
CAT_NO_ROWS_FOUND  = -808000
CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME = -809000
CAT_INVALID_RESOURCE_TYPE = -810000
CAT_INVALID_RESOURCE_CLASS = -811000
CAT_INVALID_RESOURCE_NET_ADDR = -812000
CAT_INVALID_RESOURCE_VAULT_PATH = -813000
CAT_UNKNOWN_COLLECTION = -814000
CAT_INVALID_DATA_TYPE = -815000
CAT_INVALID_ARGUMENT = -816000
CAT_UNKNOWN_FILE   = -817000
CAT_NO_ACCESS_PERMISSION = -818000
CAT_SUCCESS_BUT_WITH_NO_INFO = -819000
CAT_INVALID_USER_TYPE = -820000
CAT_COLLECTION_NOT_EMPTY = -821000
CAT_TOO_MANY_TABLES = -822000
CAT_UNKNOWN_TABLE  = -823000
CAT_NOT_OPEN       = -824000
CAT_FAILED_TO_LINK_TABLES = -825000
CAT_INVALID_AUTHENTICATION = -826000
CAT_INVALID_USER   = -827000
CAT_INVALID_ZONE   = -828000
CAT_INVALID_GROUP  = -829000
CAT_INSUFFICIENT_PRIVILEGE_LEVEL = -830000
CAT_INVALID_RESOURCE = -831000
CAT_INVALID_CLIENT_USER = -832000
CAT_NAME_EXISTS_AS_COLLECTION = -833000
CAT_NAME_EXISTS_AS_DATAOBJ = -834000
CAT_RESOURCE_NOT_EMPTY = -835000
CAT_NOT_A_DATAOBJ_AND_NOT_A_COLLECTION = -836000
CAT_RECURSIVE_MOVE  = -837000
CAT_LAST_REPLICA    = -838000
CAT_OCI_ERROR       = -839000
CAT_PASSWORD_EXPIRED = -840000
CAT_PASSWORD_ENCODING_ERROR = -850000
CAT_TABLE_ACCESS_DENIED = -851000

#RDA Errors 880000 - 900000
RDA_NOT_COMPILED_IN = -880000
RDA_NOT_CONNECTED  = -881000
RDA_ENV_ERR        = -882000
RDA_CONNECT_ERR    = -883000
RDA_DISCONNECT_ERR = -884000
RDA_CLOSE_ENV_ERR  = -885000
RDA_SQL_ERR        = -886000
RDA_CONFIG_FILE_ERR = -887000
RDA_ACCESS_PROHIBITED = -888000
RDA_NAME_NOT_FOUND = -889000

#Misc. Errors used by Obf Library 900000 - 920000
FILE_OPEN_ERR       = -900000
FILE_READ_ERR       = -901000
FILE_WRITE_ERR      = -902000
PASSWORD_EXCEEDS_MAX_SIZE = -903000
ENVIRONMENT_VAR_HOME_NOT_DEFINED = -904000
UNABLE_TO_STAT_FILE = -905000
AUTH_FILE_NOT_ENCRYPTED = -906000
AUTH_FILE_DOES_NOT_EXIST = -907000
UNLINK_FAILED       = -908000
NO_PASSWORD_ENTERED = -909000
REMOTE_SERVER_AUTHENTICATION_FAILURE = -910000
REMOTE_SERVER_AUTH_NOT_PROVIDED = -911000
REMOTE_SERVER_AUTH_EMPTY = -912000
REMOTE_SERVER_SID_NOT_DEFINED = -913000

#GSI and KRB Errors 921000 - 999000
GSI_NOT_COMPILED_IN = -921000
GSI_NOT_BUILT_INTO_CLIENT = -922000
GSI_NOT_BUILT_INTO_SERVER = -923000
GSI_ERROR_IMPORT_NAME = -924000
GSI_ERROR_INIT_SECURITY_CONTEXT = -925000
GSI_ERROR_SENDING_TOKEN_LENGTH = -926000
GSI_ERROR_READING_TOKEN_LENGTH = -927000
GSI_ERROR_TOKEN_TOO_LARGE = -928000
GSI_ERROR_BAD_TOKEN_RCVED = -929000
GSI_SOCKET_READ_ERROR = -930000
GSI_PARTIAL_TOKEN_READ = -931000
GSI_SOCKET_WRITE_ERROR = -932000
GSI_ERROR_FROM_GSI_LIBRARY = -933000
GSI_ERROR_IMPORTING_NAME = -934000
GSI_ERROR_ACQUIRING_CREDS = -935000
GSI_ACCEPT_SEC_CONTEXT_ERROR = -936000
GSI_ERROR_DISPLAYING_NAME = -937000
GSI_ERROR_RELEASING_NAME = -938000
GSI_DN_DOES_NOT_MATCH_USER = -939000
GSI_QUERY_INTERNAL_ERROR = -940000
GSI_NO_MATCHING_DN_FOUND = -941000
GSI_MULTIPLE_MATCHING_DN_FOUND = -942000
KRB_NOT_COMPILED_IN = -951000
KRB_NOT_BUILT_INTO_CLIENT = -952000
KRB_NOT_BUILT_INTO_SERVER = -953000
KRB_ERROR_IMPORT_NAME = -954000
KRB_ERROR_INIT_SECURITY_CONTEXT = -955000
KRB_ERROR_SENDING_TOKEN_LENGTH = -956000
KRB_ERROR_READING_TOKEN_LENGTH = -957000
KRB_ERROR_TOKEN_TOO_LARGE = -958000
KRB_ERROR_BAD_TOKEN_RCVED = -959000
KRB_SOCKET_READ_ERROR = -960000
KRB_PARTIAL_TOKEN_READ = -961000
KRB_SOCKET_WRITE_ERROR = -962000
KRB_ERROR_FROM_KRB_LIBRARY = -963000
KRB_ERROR_IMPORTING_NAME = -964000
KRB_ERROR_ACQUIRING_CREDS = -965000
KRB_ACCEPT_SEC_CONTEXT_ERROR = -966000
KRB_ERROR_DISPLAYING_NAME = -967000
KRB_ERROR_RELEASING_NAME = -968000
KRB_USER_DN_NOT_FOUND = -969000
KRB_NAME_MATCHES_MULTIPLE_USERS = -970000
KRB_QUERY_INTERNAL_ERROR = -971000

#Rule Engine Errors 1000000 - 1500000
OBJPATH_EMPTY_IN_STRUCT_ERR = -1000000
RESCNAME_EMPTY_IN_STRUCT_ERR = -1001000
DATATYPE_EMPTY_IN_STRUCT_ERR = -1002000
DATASIZE_EMPTY_IN_STRUCT_ERR = -1003000
CHKSUM_EMPTY_IN_STRUCT_ERR = -1004000
VERSION_EMPTY_IN_STRUCT_ERR = -1005000
FILEPATH_EMPTY_IN_STRUCT_ERR = -1006000
REPLNUM_EMPTY_IN_STRUCT_ERR = -1007000
REPLSTATUS_EMPTY_IN_STRUCT_ERR = -1008000
DATAOWNER_EMPTY_IN_STRUCT_ERR = -1009000
DATAOWNERZONE_EMPTY_IN_STRUCT_ERR = -1010000
DATAEXPIRY_EMPTY_IN_STRUCT_ERR = -1011000
DATACOMMENTS_EMPTY_IN_STRUCT_ERR = -1012000
DATACREATE_EMPTY_IN_STRUCT_ERR = -1013000
DATAMODIFY_EMPTY_IN_STRUCT_ERR = -1014000
DATAACCESS_EMPTY_IN_STRUCT_ERR = -1015000
DATAACCESSINX_EMPTY_IN_STRUCT_ERR = -1016000
NO_RULE_FOUND_ERR       = -1017000
NO_MORE_RULES_ERR       = -1018000
UNMATCHED_ACTION_ERR    = -1019000
RULES_FILE_READ_ERROR   = -1020000
ACTION_ARG_COUNT_MISMATCH = -1021000
MAX_NUM_OF_ARGS_IN_ACTION_EXCEEDED = -1022000
UNKNOWN_PARAM_IN_RULE_ERR = -1023000
DESTRESCNAME_EMPTY_IN_STRUCT_ERR = -1024000
BACKUPRESCNAME_EMPTY_IN_STRUCT_ERR = -1025000
DATAID_EMPTY_IN_STRUCT_ERR = -1026000
COLLID_EMPTY_IN_STRUCT_ERR = -1027000
RESCGROUPNAME_EMPTY_IN_STRUCT_ERR = -1028000
STATUSSTRING_EMPTY_IN_STRUCT_ERR = -1029000
DATAMAPID_EMPTY_IN_STRUCT_ERR = -1030000
USERNAMECLIENT_EMPTY_IN_STRUCT_ERR = -1031000
RODSZONECLIENT_EMPTY_IN_STRUCT_ERR = -1032000
USERTYPECLIENT_EMPTY_IN_STRUCT_ERR = -1033000
HOSTCLIENT_EMPTY_IN_STRUCT_ERR = -1034000
AUTHSTRCLIENT_EMPTY_IN_STRUCT_ERR = -1035000
USERAUTHSCHEMECLIENT_EMPTY_IN_STRUCT_ERR = -1036000
USERINFOCLIENT_EMPTY_IN_STRUCT_ERR = -1037000
USERCOMMENTCLIENT_EMPTY_IN_STRUCT_ERR = -1038000
USERCREATECLIENT_EMPTY_IN_STRUCT_ERR = -1039000
USERMODIFYCLIENT_EMPTY_IN_STRUCT_ERR = -1040000
USERNAMEPROXY_EMPTY_IN_STRUCT_ERR = -1041000
RODSZONEPROXY_EMPTY_IN_STRUCT_ERR = -1042000
USERTYPEPROXY_EMPTY_IN_STRUCT_ERR = -1043000
HOSTPROXY_EMPTY_IN_STRUCT_ERR = -1044000
AUTHSTRPROXY_EMPTY_IN_STRUCT_ERR = -1045000
USERAUTHSCHEMEPROXY_EMPTY_IN_STRUCT_ERR = -1046000
USERINFOPROXY_EMPTY_IN_STRUCT_ERR = -1047000
USERCOMMENTPROXY_EMPTY_IN_STRUCT_ERR = -1048000
USERCREATEPROXY_EMPTY_IN_STRUCT_ERR = -1049000
USERMODIFYPROXY_EMPTY_IN_STRUCT_ERR = -1050000
COLLNAME_EMPTY_IN_STRUCT_ERR = -1051000
COLLPARENTNAME_EMPTY_IN_STRUCT_ERR = -1052000
COLLOWNERNAME_EMPTY_IN_STRUCT_ERR = -1053000
COLLOWNERZONE_EMPTY_IN_STRUCT_ERR = -1054000
COLLEXPIRY_EMPTY_IN_STRUCT_ERR = -1055000
COLLCOMMENTS_EMPTY_IN_STRUCT_ERR = -1056000
COLLCREATE_EMPTY_IN_STRUCT_ERR = -1057000
COLLMODIFY_EMPTY_IN_STRUCT_ERR = -1058000
COLLACCESS_EMPTY_IN_STRUCT_ERR = -1059000
COLLACCESSINX_EMPTY_IN_STRUCT_ERR = -1060000
COLLMAPID_EMPTY_IN_STRUCT_ERR = -1062000
COLLINHERITANCE_EMPTY_IN_STRUCT_ERR = -1063000
RESCZONE_EMPTY_IN_STRUCT_ERR = -1065000
RESCLOC_EMPTY_IN_STRUCT_ERR = -1066000
RESCTYPE_EMPTY_IN_STRUCT_ERR = -1067000
RESCTYPEINX_EMPTY_IN_STRUCT_ERR = -1068000
RESCCLASS_EMPTY_IN_STRUCT_ERR = -1069000
RESCCLASSINX_EMPTY_IN_STRUCT_ERR = -1070000
RESCVAULTPATH_EMPTY_IN_STRUCT_ERR = -1071000
NUMOPEN_ORTS_EMPTY_IN_STRUCT_ERR = -1072000
PARAOPR_EMPTY_IN_STRUCT_ERR = -1073000
RESCID_EMPTY_IN_STRUCT_ERR = -1074000
GATEWAYADDR_EMPTY_IN_STRUCT_ERR = -1075000
RESCMAX_BJSIZE_EMPTY_IN_STRUCT_ERR = -1076000
FREESPACE_EMPTY_IN_STRUCT_ERR = -1077000
FREESPACETIME_EMPTY_IN_STRUCT_ERR = -1078000
FREESPACETIMESTAMP_EMPTY_IN_STRUCT_ERR = -1079000
RESCINFO_EMPTY_IN_STRUCT_ERR = -1080000
RESCCOMMENTS_EMPTY_IN_STRUCT_ERR = -1081000
RESCCREATE_EMPTY_IN_STRUCT_ERR = -1082000
RESCMODIFY_EMPTY_IN_STRUCT_ERR = -1083000
INPUT_ARG_NOT_WELL_FORMED_ERR = -1084000
INPUT_ARG_OUT_OF_ARGC_RANGE_ERR = -1085000
INSUFFICIENT_INPUT_ARG_ERR = -1086000
INPUT_ARG_DOES_NOT_MATCH_ERR = -1087000
RETRY_WITHOUT_RECOVERY_ERR = -1088000
CUT_ACTION_PROCESSED_ERR = -1089000
ACTION_FAILED_ERR        = -1090000
FAIL_ACTION_ENCOUNTERED_ERR = -1091000
VARIABLE_NAME_TOO_LONG_ERR = -1092000
UNKNOWN_VARIABLE_MAP_ERR = -1093000
UNDEFINED_VARIABLE_MAP_ERR = -1094000
NULL_VALUE_ERR           = -1095000
DVARMAP_FILE_READ_ERROR  = -1096000
NO_RULE_OR_MSI_FUNCTION_FOUND_ERR = -1097000
FILE_CREATE_ERROR        = -1098000
FMAP_FILE_READ_ERROR     = -1099000
DATE_FORMAT_ERR          = -1100000
RULE_FAILED_ERR          = -1101000
NO_MICROSERVICE_FOUND_ERR = -1102000
INVALID_REGEXP           = -1103000
INVALID_OBJECT_NAME      = -1104000
INVALID_OBJECT_TYPE      = -1105000
NO_VALUES_FOUND          = -1106000
NO_COLUMN_NAME_FOUND     = -1107000
BREAK_ACTION_ENCOUNTERED_ERR = -1108000
CUT_ACTION_ON_SUCCESS_PROCESSED_ERR = -1109000
MSI_OPERATION_NOT_ALLOWED = -1110000

#PHP Scripting Errors
PHP_EXEC_SCRIPT_ERR      = -1600000
PHP_REQUEST_STARTUP_ERR  = -1601000
PHP_OPEN_SCRIPT_FILE_ERR = -1602000

#Handler Protocol Types - these are not errors
SYS_NULL_INPUT = -99999996
SYS_HANDLER_DONE_WITH_ERROR = -99999997
SYS_HANDLER_DONE_NO_ERROR = -99999998
SYS_NO_HANDLER_REPLY_MSG = -99999999
