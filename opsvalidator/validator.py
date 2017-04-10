import pkgutil
import sys
import imp
import os
import re
from tornado.log import app_log
from opsrest import constants
from opsvalidator.base import BaseValidator, ValidationArgs

g_validators = {}


def init_plugins(plugin_dir):
    find_plugins(plugin_dir)
    register_plugins()


def find_plugins(plugin_dir):
    try:
        sys.path.append(plugin_dir)

        for entry in os.listdir(plugin_dir):
            if os.path.isfile(os.path.join(plugin_dir, entry)):
                re_results = re.search("(.+)\.py$", entry)
                if re_results:
                    module_name = re_results.groups()[0]
                    module = __import__(module_name)
                    app_log.debug(module_name + " successfully loaded.")
    except Exception as e:
        app_log.debug("Error while installing plugins:")
        app_log.debug(repr(e))


def register_plugins():
    app_log.debug("Registering plugins...")

    for plugin in BaseValidator.__subclasses__():
        if plugin.resource is not None and plugin.resource != "":
            if plugin.resource in g_validators:
                app_log.debug("%s exists, appending" % plugin.resource)
                g_validators[plugin.resource].append(plugin())
            else:
                app_log.debug("%s is a new plugin, adding" % plugin.resource)
                g_validators[plugin.resource] = [plugin()]
        else:
            app_log.info("Invalid resource defined for %s" % plugin.type())


def exec_validators(idl, schema, table_name, row, method,
                    p_table_name=None, p_row=None):
    app_log.debug("Executing validator...")

    resource_name = table_name.lower()
    if resource_name in g_validators:
        resource_validators = g_validators[resource_name]

        validation_args = ValidationArgs(idl, schema, table_name, row,
                                         p_table_name, p_row, False)

        for validator in resource_validators:
            app_log.debug("Invoking validator \"%s\" for resource \"%s\"" %
                          (validator.type(), resource_name))

            validate_by_method(validator, method, validation_args)
    else:
        app_log.debug("Custom validator for \"%s\" does not exist" %
                      resource_name)


def validate_by_method(validator, method, validation_args):
    if method == constants.REQUEST_TYPE_CREATE:
        validation_args.is_new = True
        validator.validate_modification(validation_args)
    elif method == constants.REQUEST_TYPE_UPDATE or \
         method == constants.REQUEST_TYPE_PATCH:
        validation_args.is_new = False
        validator.validate_modification(validation_args)
    elif method == constants.REQUEST_TYPE_DELETE:
        validator.validate_deletion(validation_args)
    else:
        app_log.debug("Unsupported validation for method %s" % method)
