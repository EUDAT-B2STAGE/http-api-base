# -*- coding: utf-8 -*-

"""
Integrating swagger in automatic ways.
Original source was:
https://raw.githubusercontent.com/gangverk/flask-swagger/master/flask_swagger.py

# TODO: clean unused original method or refactor...
"""

from __future__ import absolute_import

import os
import re
import inspect
from collections import defaultdict
from attr import s as AttributedModel, ib as attribute
from . import BASE_URLS, STATIC_URL, CORE_DIR, USER_CUSTOM_DIR
from .logs import get_logger, pretty_print
from .formats.yaml import yaml, load_yaml_file

log = get_logger(__name__)


def _sanitize(comment):
    return comment.replace('\n', '<br/>') if comment else comment


def _find_from_file(full_doc, from_file_keyword):
    """
    Finds a line in <full_doc> like

        <from_file_keyword> <colon> <path>

    and return path
    """
    path = None

    for line in full_doc.splitlines():
        if from_file_keyword in line:
            parts = line.strip().split(':')
            if len(parts) == 2 and parts[0].strip() == from_file_keyword:
                path = parts[1].strip()
                break

    return path


def _doc_from_file(path):
    doc = None
    with open(path) as f:
        doc = f.read()
    return doc


def _parse_docstring(obj, process_doc, from_file_keyword, path=None):

    first_line, other_lines, swag = None, None, None
    full_doc = inspect.getdoc(obj)

    if full_doc or path is not None:
        # print("TEST", full_doc)

        # FROM FILE
        if from_file_keyword is not None:

            if path is None:
                from_file = _find_from_file(full_doc, from_file_keyword)
            else:
                ############################
                # CUSTOM BY US
                # Forcing reading from file
                # if having a path automatically generated
                ############################
                from_file = path

            if from_file:
                # log.debug("Reading from file %s" % from_file)
                full_doc_from_file = _doc_from_file(from_file)
                if full_doc_from_file:
                    full_doc = full_doc_from_file

        line_feed = full_doc.find('\n')
        if line_feed != -1:
            first_line = process_doc(full_doc[:line_feed])
            yaml_sep = full_doc[line_feed + 1:].find('---')
            if yaml_sep != -1:
                other_lines = process_doc(
                    full_doc[line_feed + 1:line_feed + yaml_sep])
                swag = yaml.load(full_doc[line_feed + yaml_sep:])
            else:
                other_lines = process_doc(full_doc[line_feed + 1:])
        else:
            first_line = full_doc

    return first_line, other_lines, swag


def _extract_definitions(alist, level=None):
    """
    Since we couldn't be bothered to register models elsewhere
    our definitions need to be extracted from the parameters.
    We require an 'id' field for the schema to be correctly
    added to the definitions list.
    """

    def _extract_array_defs(source):
        # extract any definitions that are within arrays
        # this occurs recursively
        ret = []
        items = source.get('items')
        if items is not None and 'schema' in items:
            ret += _extract_definitions([items], level + 1)
        return ret

    # for tracking level of recursion
    if level is None:
        level = 0

    defs = list()
    if alist is not None:
        for item in alist:
            schema = item.get("schema")
            if schema is not None:
                schema_id = schema.get("id")
                if schema_id is not None:
                    defs.append(schema)
                    ref = {"$ref": "#/definitions/{}".format(schema_id)}

                    # only add the reference as a schema
                    # if we are in a response or a parameter
                    # i.e. at the top level directly ref
                    # if a definition is used within another definition
                    if level == 0:
                        item['schema'] = ref
                    else:
                        item.update(ref)
                        del item['schema']

                # extract any definitions that are within properties
                # this occurs recursively
                properties = schema.get('properties')
                if properties is not None:
                    defs += _extract_definitions(
                        properties.values(), level + 1)

                defs += _extract_array_defs(schema)

            defs += _extract_array_defs(item)

    return defs


def swagger(app, package_root='',
            prefix=None, process_doc=_sanitize,
            from_file_keyword=None, template=None):
    """
    Call this from an @app.route method like this
    @app.route('/spec.json')
    def spec():
       return jsonify(swagger(app))

    We go through all endpoints of the app searching for swagger endpoints
    We provide the minimum required data according to swagger specs
    Callers can and should add and override at will

    Arguments:
    app -- the flask app to inspect

    Keyword arguments:
    process_doc -- text sanitization method,
    the default simply replaces \n with <br>
    from_file_keyword -- how to specify a file to load doc from
    template -- The spec to start with and update as flask-swagger finds paths.
    """
    output = {
        "swagger": "2.0",
        "info": {
            "version": "0.0.1",
            "title": "Application name",
        }
    }
    paths = defaultdict(dict)
    definitions = defaultdict(dict)
    if template is not None:
        output.update(template)
        # check for template provided paths and definitions
        for k, v in output.get('paths', {}).items():
            paths[k] = v
        for k, v in output.get('definitions', {}).items():
            definitions[k] = v
    output["paths"] = paths
    output["definitions"] = definitions

    ignore_verbs = {"HEAD", "OPTIONS"}
    # technically only responses is non-optional
    optional_fields = [
        'tags', 'consumes', 'produces', 'schemes', 'security', 'deprecated',
        'operationId', 'externalDocs'
    ]

    for rule in app.url_map.iter_rules():

        endpoint = app.view_functions[rule.endpoint]
        methods = dict()

        for verb in rule.methods.difference(ignore_verbs):
            verb = verb.lower()
            if hasattr(endpoint, 'methods') \
                    and verb in map(lambda m: m.lower(), endpoint.methods) \
                    and hasattr(endpoint.view_class, verb):
                methods[verb] = getattr(endpoint.view_class, verb)
            else:
                methods[verb] = endpoint

        # clean rule
        myrule = str(rule)
        if myrule.startswith(STATIC_URL):
            continue
        for prefix in BASE_URLS:
            if myrule.startswith(prefix):
                myrule = myrule.replace(prefix, '', 1)

        if 'view_class' not in dir(endpoint):
            log.warning("Un-Swaggable endpoint path %s" % rule)
            continue

        operations = dict()
        for verb, method in methods.items():

            # ###########
            # TODO: finish this up
            from commons import CONFIG_DIR
            subdir = USER_CUSTOM_DIR
            if getattr(endpoint.view_class, '_is_base', False):
                subdir = CORE_DIR
            folder = myrule.strip('/')

            if folder.endswith('>'):
                # print("TO THINK OF IT", folder, method)
                continue

            path = os.path.join(
                package_root, CONFIG_DIR, subdir, folder,
                method.__name__ + '.yaml')

            log.debug("Looking for %s" % path)
            # ###########

            swag = None
            # Note: using parse method only inside this conditional block
            # WE AVOID documentation which is written inside the docstring
            if os.path.exists(path):
                summary, description, swag = \
                    _parse_docstring(
                        method, process_doc, from_file_keyword, path)
                print("Found file", swag)
            else:
                # summary, description, swag = \
                #     _parse_docstring(method, process_doc, from_file_keyword)
                pass

            if swag is not None:
                print("Found swag definitions")
                # we only add endpoints with swagger data in the docstrings
                defs = swag.get('definitions', [])
                defs = _extract_definitions(defs)
                params = swag.get('parameters', [])
                defs += _extract_definitions(params)
                responses = swag.get('responses', {})
                responses = {
                    str(key): value
                    for key, value in responses.items()
                }
                if responses is not None:
                    defs = defs + _extract_definitions(responses.values())
                for definition in defs:
                    def_id = definition.pop('id')
                    if def_id is not None:
                        definitions[def_id].update(definition)
                operation = dict(
                    summary=summary,
                    description=description,
                    responses=responses
                )
                # parameters - swagger ui dislikes empty parameter lists
                if len(params) > 0:
                    operation['parameters'] = params
                # other optionals
                for key in optional_fields:
                    if key in swag:
                        operation[key] = swag.get(key)
                operations[verb] = operation

        if len(operations):
            rule = str(rule)
            for arg in re.findall('(<([^<>]*:)?([^<>]*)>)', rule):
                rule = rule.replace(arg[0], '{%s}' % arg[2])
            paths[rule].update(operations)
    return output


# def _parse_file(path):
#     """
#     Hand made from the original
#     with the main goal of reading a swagger file definition
#     """

#     log.debug("Reading swagger in %s" % path)
#     first_line, other_lines, swag = None, None, None
#     full_doc = _doc_from_file(path)

#     line_feed = full_doc.find('\n')
#     if line_feed != -1:
#         first_line = _sanitize(full_doc[:line_feed])
#         yaml_sep = full_doc[line_feed + 1:].find('---')
#         if yaml_sep != -1:
#             other_lines = _sanitize(
#                 full_doc[line_feed + 1:line_feed + yaml_sep])
#             swag = yaml.load(full_doc[line_feed + yaml_sep:])
#         else:
#             other_lines = _sanitize(full_doc[line_feed + 1:])
#     else:
#         first_line = full_doc

#     return first_line, other_lines, swag


# TODO: this should probably become a class...
class BeSwagger(object):

    def __init__(self, endpoints):
        self._endpoints = endpoints
        self._paths = {}

    def read_my_swagger(self, file, method, uris={}):

        ################################
        # NOTE: the file reading here is cached
        # you can read it multiple times with no overload
        mapping = load_yaml_file(file)

        # content has to be a dictionary
        if not isinstance(mapping, dict):
            raise TypeError("Wrong method ")

        ################################
        # A way to save external attributes
        @AttributedModel
        class ExtraAttributes(object):
            auth = attribute(default=[])  # bool

        extra = ExtraAttributes()

        # read common
        commons = mapping.pop('common', {})

        ################################
        # Specs should contain only labels written in spec before
        for label, specs in mapping.items():
            if label not in uris:
                raise KeyError(
                    "Invalid label '%s' found.\nAvailable labels: %s"
                    % (label, list(uris.keys())))
            uri = uris[label]
            print("SWAGGERING", method, uri)
            if uri not in self._paths:
                self._paths[uri] = {}

            ################################
            # add common elements to all specs
            for key, value in commons.items():
                if key not in specs:
                    specs[key] = value

            ################################
            # Separate external definitions

            # Find the custom part
            custom = specs.pop('custom', {})

            # Authentication
            if custom.get('authentication', False):

                roles = custom.get('authorized', [])
                for role in roles:
                    # check if this role makes sense?
                    # TODO: create a method inside 'auth' to check roles
                    pass

                    extra.auth = roles

            # Other custom elements?
            # NOTE: whatever is left will be parsed into Swagger Validator

            ###########################
            # pretty_print(specs)
            self._paths[uri][method] = specs

        return extra

    def swaggerish(self):
        """
        Go through all endpoints configured by the current development.

        Provide the minimum required data according to swagger specs.
        """

        # A template base
        output = {
            "swagger": "2.0",
            "info": {
                "version": "0.0.1",
                "title": "Your application name",
            }
        }

        # Set existing values
        from commons.globals import mem
        proj = mem.custom_config['project']
        if 'version' in proj:
            output['info']['version'] = proj['version']
        if 'title' in proj:
            output['info']['title'] = proj['title']

        for endpoint in self._endpoints:

            endpoint.custom = {}

            for method, file in endpoint.methods.items():

                endpoint.custom[method] = \
                    self.read_my_swagger(file, method, endpoint.uris)

        output['paths'] = self._paths
        return output

    @staticmethod
    def validation(swag_dict):
        """
        Based on YELP library,
        verify the current definition on the open standard
        """

        from bravado_core.spec import Spec

        bravado_config = {
            'validate_swagger_spec': True,
            'validate_requests': False,
            'validate_responses': False,
            'use_models': False,
        }

        try:
            print(swag_dict)
            Spec.from_dict(swag_dict, config=bravado_config)
            log.info("Validated")
        except Exception as e:
            error = str(e).split('\n')[0]
            log.error("Failed to validate:\n%s\n" % error)
            return False

        return True
