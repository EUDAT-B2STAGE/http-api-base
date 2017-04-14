# -*- coding: utf-8 -*-

"""
Detect which services are running, by testing environment variables
set with containers/docker-compose/do.py

Note: docker links and automatic variables removed as unsafe with compose V3

"""

import os
# from functools import lru_cache
from rapydo.confs import CORE_CONFIG_PATH
from rapydo.confs import CUSTOM_PACKAGE
from rapydo.utils.meta import Meta
from rapydo.utils.formats.yaml import load_yaml_file

from rapydo.utils.logs import get_logger


log = get_logger(__name__)


class Detector(object):

    def __init__(self, config_file_name='services'):

        self.authentication_service = None
        self.authentication_name = 'authentication'
        self.task_service_name = 'celery'
        self.modules = []
        self.services_configuration = []
        self.services = {}
        self.services_classes = {}
        self.extensions_instances = {}
        self.available_services = {}

        self.meta = Meta()
        self.check_configuration(config_file_name)
        self.load_classes()

    @staticmethod
    def get_bool_from_os(name):
        bool_var = os.environ.get(name, False)
        if not isinstance(bool_var, bool):
            tmp = int(bool_var)
            bool_var = bool(tmp)
        return bool_var

    @staticmethod
    # @lru_cache(maxsize=None)
    def prefix_name(service):
        return \
            service.get('name'), \
            service.get('prefix').lower() + '_'

    def check_configuration(self, config_file_name):

        self.services_configuration = load_yaml_file(
            file=config_file_name, path=CORE_CONFIG_PATH)

        for service in self.services_configuration:

            name, prefix = self.prefix_name(service)

            # Was this service enabled from the developer?
            enable_var = str(prefix + 'enable').upper()
            self.available_services[name] = self.get_bool_from_os(enable_var)
            if self.available_services[name]:

                # read variables
                variables = self.load_variables(service, enable_var, prefix)
                service['variables'] = variables

                # set auth service
                if name == self.authentication_name:
                    self.authentication_service = variables.get('service')

        # log.pp(self.services_configuration)

        if self.authentication_service is None:
            raise AttributeError("no service defined behind authentication")
        else:
            log.info("Authentication based on '%s' service"
                     % self.authentication_service)

    def load_variables(self, service, enable_var=None, prefix=None):

        variables = {}

        if prefix is None:
            _, prefix = self.prefix_name(service)

        for var, value in os.environ.items():
            if enable_var is not None and var == enable_var:
                continue
            var = var.lower()
            if var.startswith(prefix):
                key = var[len(prefix):]
                variables[key] = value

        # Is this service external?
        external_var = str(prefix + 'external').upper()
        variables['external'] = self.get_bool_from_os(external_var)

        return variables

    def load_class_from_module(self, classname='BaseInjector', service=None):

        if service is None:
            flaskext = ''
        else:
            flaskext = '.' + service.get('extension')

        # Try inside our extensions
        module = self.meta.get_module_from_string(
            modulestring='flask_ext' + flaskext, exit_on_fail=True)
        if module is None:
            log.critical_exit("Missing %s for %s" % (flaskext, service))

        return getattr(module, classname)

    def load_classes(self):

        for service in self.services_configuration:

            name, _ = self.prefix_name(service)

            if self.available_services.get(name):
                log.very_verbose("Looking for class %s" % name)
            else:
                continue

            variables = service.get('variables')
            ext_name = service.get('class')

            # Get the existing class
            MyClass = self.load_class_from_module(ext_name, service=service)

            # Passing variables
            MyClass.set_variables(variables)

            # Passing models
            if service.get('load_models'):
                MyClass.set_models(
                    self.meta.import_models(name, custom=False),
                    self.meta.import_models(
                        name, custom=True, exit_on_fail=False)
                )
            else:
                log.very_verbose("Skipping models")

            # Save
            self.services_classes[name] = MyClass
            log.debug("Got class definition for %s" % MyClass)

        if len(self.services_classes) < 1:
            raise KeyError("No classes were recovered!")

        return self.services_classes

    def init_services(self, app, worker_mode=False):

        instances = {}
        auth_backend = None

        for service in self.services_configuration:

            name, _ = self.prefix_name(service)

            if not self.available_services.get(name):
                continue

            if name == self.authentication_name and auth_backend is None:
                raise ValueError("No backend service recovered")

            args = {}
            if name == self.task_service_name:
                args['worker_mode'] = worker_mode

            ExtClass = self.services_classes.get(name)
            ext_instance = ExtClass(app, **args)

            log.debug("Initializing %s" % name)
            service_instance = ext_instance.custom_init(auth_backend)
            instances[name] = service_instance

            if name == self.authentication_service:
                auth_backend = service_instance

            self.extensions_instances[name] = ext_instance

            # Injecting into the Celery Extension Class
            # all celery tasks found in *vanilla_package/tasks*
            if name == self.task_service_name:

                task_package = "%s.tasks" % CUSTOM_PACKAGE

                submodules = \
                    self.meta.import_submodules_from_package(task_package)
                for submodule in submodules:
                    tasks = self.meta.get_celery_tasks_from_module(submodule)

                    for func_name, funct in tasks.items():
                        setattr(ExtClass, func_name, funct)

        self.project_initialization(instances)

        if len(self.extensions_instances) < 1:
            raise KeyError("No instances available for modules")

        return self.extensions_instances

    def load_injector_modules(self):

        for service in self.services_configuration:

            name, _ = self.prefix_name(service)
            if not self.available_services.get(name):
                continue

            # Module for injection
            ModuleBaseClass = self.load_class_from_module()
            # Create modules programmatically 8)
            MyModule = self.meta.metaclassing(
                ModuleBaseClass, service.get('injector'))

            # Recover class
            MyClass = self.services_classes.get(name)
            if MyClass is None:
                raise AttributeError("No class found for %s" % name)
            MyModule.set_extension_class(MyClass)
            self.modules.append(MyModule)

        return self.modules

    def check_availability(self, name):

        if '.' in name:
            # In this case we are receiving a module name
            # e.g. rapydo.services.mongodb
            name = name.split('.')[::-1][0]

        return self.available_services.get(name)

    @classmethod
    def project_initialization(self, instances):
        """ Custom initialization of your project

        Please define your class Initializer in
        vanilla/project/initialization.py
        """

        log.critical("Global project initialization to be fullfilled")
        # print("INIT WHATEVER?", instances, "\n\n")

        try:
            module_path = "%s.%s.%s" % \
                (CUSTOM_PACKAGE, 'project', 'initialization')
            module = self.meta.get_module_from_string(module_path)
            Initializer = self.meta.get_class_from_string(
                'Initializer', module)
            Initializer()
            log.debug("Project has been initialized")
        except BaseException:
            log.debug("No custom init available for mixed services")


detector = Detector()
