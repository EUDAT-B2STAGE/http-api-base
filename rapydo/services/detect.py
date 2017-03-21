# -*- coding: utf-8 -*-

"""
Detect which services are running, by testing environment variables
set with containers/docker-compose/do.py

Note: links and automatic variables were removed as unsafe
"""

import os
from rapydo.confs import CORE_CONFIG_PATH
from rapydo.utils.meta import Meta
from rapydo.utils.formats.yaml import load_yaml_file
from rapydo.utils.logs import get_logger


log = get_logger(__name__)

meta = Meta()
services_configuration = load_yaml_file('services', path=CORE_CONFIG_PATH)

authentication_service = None
services = {}
services_classes = {}
available_services = {}

# Work off all available services
for service in services_configuration:

    name = service.get('name')
    prefix = service.get('prefix').lower() + '_'

    # Was this service enabled from the developer?
    enable_var = prefix.upper() + 'ENABLE'
    available_services[name] = os.environ.get(enable_var, False)

    if available_services.get(name):
        log.very_verbose("Service %s: requested to be enabled" % name)

        # Is this service external?
        external_var = prefix + 'EXTERNAL'
        if os.environ.get(external_var) is None:
            os.environ[external_var] = "False"

        ###################
        # Read variables
        variables = {}
        for var, value in os.environ.items():
            if var == enable_var:
                continue
            var = var.lower()
            if var.startswith(prefix):
                key = var[len(prefix):]
                variables[key] = value

        key = 'injected_name'
        variables[key] = service.get(key)

        if name == 'authentication':
            authentication_service = variables.get('service')

        ###################
        # Load module and get class and configuration
        flaskext = service.get('extension')

        # Try inside our extensions
        module = meta.get_module_from_string('flask_ext.' + flaskext)

        # Try inside normal flask extensions
        if module is None:
            module = meta.get_module_from_string(flaskext)
            if module is None:
                log.error("Missing %s for service %s" % (flaskext, name))
                exit(1)
            else:
                log.very_verbose("Loaded external extension %s" % name)
        else:
            # log.very_verbose("Loaded internal extension %s" % name)
            pass

        ###################
        Configurator = getattr(module, service.get('injector'))
        # Passing variables
        Configurator.set_variables(variables)
        # Passing models
        if service.get('load_models'):
            Configurator.set_models(
                meta.import_models(name, custom=False),
                meta.import_models(name, custom=True, exit_on_fail=False)
            )
        else:
            log.debug("Skipping models")

        ###################
        Class = getattr(module, service.get('class'))

        # ###################
        # TO DO: elaborate this OPTIONAL concept
        # # Is this service optional?
        # variables.get('optional', False)
        # print(variables)

        # Save services
        services[name] = Configurator
        services_classes[name] = Class

    else:
        log.very_verbose("Skipping service %s" % name)

# TODO: should we report error if missing authentication?
if authentication_service is None:
    raise AttributeError("Missing config: no service behind authentication")
else:
    log.info("Authentication based on: '%s' service" % authentication_service)
