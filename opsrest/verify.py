# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from opsrest import parse
from opsrest.utils import utils
from opsrest.constants import *
from opsrest.exceptions import DataValidationFailed

import types

from tornado.log import app_log
from ovs.db import types as ovs_types


def verify_http_method(resource, schema, http_method):
    '''
    Operations are allowed on each schema table/resource:
     - GET: any table with at least one attribute tagged as
       category:[configuration|status|statistics] can be retrieved.
     - PUT/PATCH: any table with at least one attribute tagged as
       category:configuration (relationship or not) can be updated.
     - POST/DELETE: any root table with an index attribute tagged as
       category:configuration OR any non-root table referenced by an attribute
       tagged as category:configuration can be created/deleted.
    '''
    # only GET/PUT/PATCH is allowed on System table
    if resource.next is None and resource.table == 'System':
        if http_method == REQUEST_TYPE_UPDATE or \
                http_method == REQUEST_TYPE_READ or \
                http_method == REQUEST_TYPE_PATCH:
            return True
        else:
            return False

    resource_table = schema.ovs_tables[resource.next.table]
    is_root = resource_table.is_root
    resource_indexes = resource_table.indexes
    resource_config = resource.next.keys[OVSDB_SCHEMA_CONFIG]
    resource_refs = resource.next.keys[OVSDB_SCHEMA_REFERENCE]
    parent_refs = resource.keys[OVSDB_SCHEMA_REFERENCE]

    # look for config references
    resource_config_refs = []
    for name, ref in resource_refs.iteritems():
        if ref.category == OVSDB_SCHEMA_CONFIG:
            resource_config_refs.append(name)

    parent_config_refs = []
    for name, ref in parent_refs.iteritems():
        if ref.category == OVSDB_SCHEMA_CONFIG:
            parent_config_refs.append(name)

    if http_method == REQUEST_TYPE_READ:
        return True

    elif http_method == REQUEST_TYPE_UPDATE or \
            http_method == REQUEST_TYPE_PATCH:
        # check if at least one attribute is tagged as category:configuration
        if len(resource_config) > 0 or len(resource_config_refs) > 0:
            return True
        else:
            return False

    elif http_method == REQUEST_TYPE_CREATE or \
            http_method == REQUEST_TYPE_DELETE:
        # root table
        if is_root:
            # is index 'uuid'
            if len(resource_indexes) == 1 and resource_indexes[0] == 'uuid':
                return True
            # non-uuid index
            for index in resource_indexes:
                if (index in resource_config or
                        index in resource_config_refs):
                    return True
        # non-root table
        else:
            if resource.column is not None:
                if resource.column in parent_config_refs:
                    return True
            # Ex. Ports
            elif resource.relation == OVSDB_SCHEMA_TOP_LEVEL:
                return True

        return False


def verify_data(data, resource, schema, idl, http_method):

    if http_method == REQUEST_TYPE_CREATE:
        return verify_post_data(data, resource, schema, idl)
    elif http_method == REQUEST_TYPE_UPDATE:
        return verify_put_data(data, resource, schema, idl)
    elif http_method == REQUEST_TYPE_PATCH:
        return verify_patch_data(data, resource, schema, idl)


def verify_post_data(data, resource, schema, idl):

    if OVSDB_SCHEMA_CONFIG not in data:
        raise DataValidationFailed("Missing %s data" % OVSDB_SCHEMA_CONFIG)

    _data = data[OVSDB_SCHEMA_CONFIG]

    # verify config and reference columns data
    verified_data = {}

    # when adding a child with kv_type of forward referencing,
    # the configuration data must contain the 'keyname' used to
    # identify the reference of the new resource created.
    if resource.relation is OVSDB_SCHEMA_CHILD:
        ref = resource.keys[OVSDB_SCHEMA_REFERENCE][resource.column]
        reference = ref
        if reference.kv_type:
            keyname = reference.keyname
            if keyname not in _data:
                error = "Missing keyname attribute to" +\
                        " reference the new resource" +\
                        " from the parent"

                raise DataValidationFailed(error)
            else:
                verified_data[keyname] = _data[keyname]
                _data.pop(keyname)

    try:
        # verify configuration data, add it to verified data
        verified_config_data = verify_config_data(resource.next,
                                                  _data,
                                                  schema,
                                                  REQUEST_TYPE_CREATE)

        verified_data.update(verified_config_data)

        # verify reference data, add it to verified data
        verified_reference_data = verify_forward_reference(_data,
                                                           resource.next,
                                                           schema, idl)
        verified_data.update(verified_reference_data)

        # a non-root top-level table must be referenced by another resource
        # or ovsdb-server will garbage-collect it
        is_root = schema.ovs_tables[resource.next.table].is_root
        if resource.relation == OVSDB_SCHEMA_TOP_LEVEL and not is_root:
            if OVSDB_SCHEMA_REFERENCED_BY not in data:
                error = "Missing %s" % OVSDB_SCHEMA_REFERENCED_BY
                raise DataValidationFailed(error)

            _data = data[OVSDB_SCHEMA_REFERENCED_BY]
            verified_referenced_by_data = verify_referenced_by(_data,
                                                               resource.next,
                                                               schema, idl)
            verified_data.update(verified_referenced_by_data)

        elif resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
            references = resource.next.keys[OVSDB_SCHEMA_REFERENCE]
            for key, value in references.iteritems():
                if value.relation == 'parent':
                    parent_row = idl.tables[resource.table].rows[resource.row]
                    verified_data.update({key: parent_row})

    except DataValidationFailed as e:
        raise e

    # data verified
    return verified_data


def verify_put_data(data, resource, schema, idl):

    if OVSDB_SCHEMA_CONFIG not in data:
        raise DataValidationFailed("Missing %s data" % OVSDB_SCHEMA_CONFIG)

    _data = data[OVSDB_SCHEMA_CONFIG]

    # We neet to verify System table
    if resource.next is None:
        resource_verify = resource
    else:
        resource_verify = resource.next

    # Get the targeted row
    row = idl.tables[resource_verify.table].rows[resource_verify.row]

    # verify config and reference columns data
    verified_data = {}
    try:
        verified_config_data = verify_config_data(resource_verify,
                                                  _data,
                                                  schema,
                                                  REQUEST_TYPE_UPDATE,
                                                  row)

        verified_data.update(verified_config_data)

        verified_reference_data = verify_forward_reference(_data,
                                                           resource_verify,
                                                           schema, idl)
        verified_data.update(verified_reference_data)

        is_root = schema.ovs_tables[resource_verify.table].is_root

        # Reference by is not allowed in put
        if resource.relation == OVSDB_SCHEMA_TOP_LEVEL and not is_root:
            if OVSDB_SCHEMA_REFERENCED_BY in data:
                app_log.info('referenced_by is not allowed for PUT')
                error = "Attribute %s not allowed for PUT"\
                        % OVSDB_SCHEMA_REFERENCED_BY
                raise DataValidationFailed(error)

    except DataValidationFailed as e:
        raise e

    # data verified
    return verified_data


def verify_patch_data(data, resource, schema, idl):

    # We need to verify System table
    if resource.next is None:
        resource_verify = resource
    else:
        resource_verify = resource.next

    # verify config and reference columns data
    verified_data = {}
    try:
        verified_config_data = verify_config_data(resource_verify,
                                                  data,
                                                  schema,
                                                  REQUEST_TYPE_PATCH)

        verified_data.update(verified_config_data)

        verified_reference_data = verify_forward_reference(data,
                                                           resource_verify,
                                                           schema, idl)
        verified_data.update(verified_reference_data)

    except DataValidationFailed as e:
        raise e

    # data verified
    return verified_data


def verify_config_data(resource, data, schema, request_type,
                       row=None, get_all_errors=False):

    config_keys = resource.keys[OVSDB_SCHEMA_CONFIG]
    reference_keys = resource.keys[OVSDB_SCHEMA_REFERENCE]

    verified_config_data = {}
    errors = []

    # Check for extra or unknown attributes
    unknown_attribute = find_unknown_attribute(data,
                                               config_keys,
                                               reference_keys)
    if unknown_attribute is not None:
        error = "Unknown configuration attribute: %s" % unknown_attribute
        if get_all_errors:
            errors.append(error)
        else:
            raise DataValidationFailed(error)

    non_mutable_attributes = get_non_mutable_attributes(resource,
                                                        schema)

    # Check for all required/valid attributes to be present
    for column_name in config_keys:
        is_optional = config_keys[column_name].is_optional

        if column_name in data:
            try:
                verify_attribute_type(column_name, config_keys[column_name],
                                      data[column_name])
                verify_attribute_range(column_name, config_keys[column_name],
                                       data[column_name])
            except DataValidationFailed as e:
                if get_all_errors:
                    errors.append(e.detail)
                else:
                    raise e

            if request_type == REQUEST_TYPE_CREATE:
                verified_config_data[column_name] = data[column_name]
            elif request_type in (REQUEST_TYPE_UPDATE, REQUEST_TYPE_PATCH):
                if column_name not in non_mutable_attributes:
                    verified_config_data[column_name] = data[column_name]
                else:
                    # Check if immutable attribute is being updated
                    if row is not None:
                        if is_optional:
                            column_list = []
                            column_list.append(data[column_name])
                            if row.__getattr__(column_name) != column_list:
                                error = "Attribute list '%s' cannot be modified" % column_name
                                raise DataValidationFailed(error)
                        elif row.__getattr__(column_name) != data[column_name]:
                            error = "Attribute '%s' cannot be modified" % column_name
                            raise DataValidationFailed(error)

        else:
            # PUT ignores immutable attributes, otherwise they are required.
            # If it's a PUT request, and the field is a mutable and mandatory,
            # but not found, then it's an error.
            #
            # POST requires all attributes. If it's a mandatory field not found
            # then it's an error.
            if request_type in (REQUEST_TYPE_UPDATE, REQUEST_TYPE_PATCH) and \
                    column_name in non_mutable_attributes:
                continue

            if not is_optional:
                error = "Attribute %s is required" % column_name
                if get_all_errors:
                    errors.append(error)
                else:
                    raise DataValidationFailed(error)

    if len(errors):
        raise DataValidationFailed(errors)
    else:
        return verified_config_data


def verify_attribute_type(column_name, column_data, request_data):
    data = request_data
    data_type = type(data)
    valid_types = column_data.type.python_types

    # If column is a list, data must be a list
    if column_data.is_list:
        valid_types = [list]

    # If column is a dictionary, data must be a dictionary
    elif column_data.is_dict:
        valid_types = [dict]

    # If data is a list but column is not,
    # we expect a single value in the list
    elif data_type is list:
        if len(data) == 1:
            data = data[0]
            data_type = type(data)

    try:
        if data_type in valid_types:

            # Check each value's type for elements in lists and dictionaries
            if column_data.n_max > 1:
                verify_container_values_type(column_name, column_data,
                                             request_data)

            # Now check for invalid values
            verify_valid_attribute_values(data, column_data,
                                          column_name)
        else:
            error = "Attribute type mismatch for column %s" % column_name
            raise DataValidationFailed(error)
    except DataValidationFailed as e:
        raise e


def verify_container_values_type(column_name, column_data, request_data):

    if column_data.is_list:
        for value in request_data:
            if type(value) not in column_data.type.python_types:
                error = "Value type mismatch in column %s" % column_name
                raise DataValidationFailed(error)

    elif column_data.is_dict:
        for key, value in request_data.iteritems():
            # Check if request data has unknown keys for columns other than
            # those in OVSDB_COMMON_COLUMNS (which should accept any keys).
            # Note: common columns which do not require key validation should
            # be added to OVSDB_COMMON_COLUMNS array.
            if column_name not in OVSDB_COMMON_COLUMNS:
                if column_data.kvs and key not in column_data.kvs:
                    error = "Unknown key %s for column %s" % (key, column_name)
                    raise DataValidationFailed(error)

            value_type = type(value)

            # Values in dict must match JSON schema
            if value_type in column_data.value_type.python_types:

                # If they match, they might be strings that represent other
                # types, so each value must be checked if kvs type exists

                if value_type in ovs_types.StringType.python_types \
                        and column_data.kvs and key in column_data.kvs:
                    kvs_value_type = column_data.kvs[key]['type']
                    converted_value = \
                        convert_string_to_value_by_type(value, kvs_value_type)

                    if converted_value is None:
                        error = "Value type mismatch for key %s in column %s"\
                                % (key, column_name)
                        raise DataValidationFailed(error)
            else:
                error = "Value type mismatch for key %s in column %s"\
                        % (key, column_name)
                raise DataValidationFailed(error)


def convert_string_to_value_by_type(value, type_):

    converted_value = value

    if type_ == ovs_types.IntegerType or \
            type_ in ovs_types.IntegerType.python_types:
        try:
            converted_value = int(value)
        except ValueError:
            converted_value = None
    elif type_ == ovs_types.RealType or \
            type_ in ovs_types.RealType.python_types:
        try:
            converted_value = float(value)
        except ValueError:
            converted_value = None
    elif type_ == ovs_types.BooleanType or \
            type_ in ovs_types.BooleanType.python_types:
        if not (value == 'true' or value == 'false'):
            converted_value = None

    return converted_value


def verify_valid_attribute_values(request_data, column_data, column_name):

    valid = True

    error_details = ""
    error_message = "Attribute value is invalid for column '%s'." % column_name

    # If data has key-values dict defined, check for missing/invalid keys
    # It's assumed type is validated, meaning kvs is defined for dicts only
    if column_data.kvs:

        valid_keys = set(column_data.kvs.keys())
        data_keys = set(request_data.keys())
        unknown_keys = []
        if column_name not in OVSDB_COMMON_COLUMNS:
            unknown_keys = data_keys.difference(valid_keys)
        missing_keys = valid_keys.difference(data_keys)

        if unknown_keys:
            error_details += "Unknown keys: '%s'. " % list(unknown_keys)

        if missing_keys:
            true_missing_keys = []

            for key in missing_keys:
                if not column_data.kvs[key]["is_optional"]:
                    true_missing_keys.append(key)

            if true_missing_keys:
                missing_keys = true_missing_keys
                error_details += "Missing keys: '%s'. " % list(missing_keys)
            else:
                missing_keys = []

        if unknown_keys or missing_keys:
            valid = False

        if valid:
            # Now that keys have been checked,
            # verify their values are valid
            for key, value in column_data.kvs.iteritems():
                if key in request_data and value['enum']:
                    enum = set(value['enum'].as_list())

                    data_value = request_data[key]

                    if type(data_value) \
                            in ovs_types.StringType.python_types:
                        data_value = \
                            convert_string_to_value_by_type(data_value,
                                                            value['type'])

                    if not is_value_in_enum(data_value, enum):
                        valid = False
                        error_details += "Invalid value for key '%s'. " % key
                        break

    # If data has an enum defined, check for a valid value
    elif column_data.enum:

        enum = set(column_data.enum.as_list())
        valid = is_value_in_enum(request_data, enum)

    if not valid:
        if error_details:
            error_message += ": " + error_details
        raise DataValidationFailed(error_message)


def is_value_in_enum(value, enum):

    valid = True

    # Check if request's list contains values not valid
    if type(value) is list:
        if set(value).difference(enum):
            valid = False

    # Check if single request value is valid
    elif value not in enum:
        valid = False

    return valid


def verify_attribute_range(column_name, column_data, request_data):

    # We assume verify_attribute_type has already been called,
    # so request_data type must be correct (save for a small
    # exception if column is list)

    data_type = type(request_data)

    # Check elements in in a list
    if column_data.is_list:

        # Exception: a single value might be accepted
        # by OVSDB as a single element list
        request_list = []
        if data_type is not list:
            request_list.append(request_data)
        else:
            request_list = request_data

        request_len = len(request_list)
        if request_len < column_data.n_min or request_len > column_data.n_max:
            error = "List number of elements is out of range for column %s" % \
                column_name
            raise DataValidationFailed(error)
        else:
            for element in request_list:
                # We usually check the value itself
                # But for a string, we check its length instead
                value = element
                if type(element) in ovs_types.StringType.python_types:
                    value = len(element)

                if (value < column_data.rangeMin or
                        value > column_data.rangeMax):
                    error = "List element %s is out of range for column %s" % \
                        (element, column_name)
                    raise DataValidationFailed(error)

    # Check elements in a dictionary
    elif column_data.is_dict:
        request_len = len(request_data)
        if request_len < column_data.n_min or request_len > column_data.n_max:
            error = "Dict number of elements is out of range for column %s" % \
                column_name
            raise DataValidationFailed(error)
        else:
            for key, data in request_data.iteritems():

                # First check the key
                # TODO is this necessary? Valid keys are verified prior to this

                value = key
                if type(key) in ovs_types.StringType.python_types:
                    value = len(key)

                if (value < column_data.rangeMin or
                        value > column_data.rangeMax):
                    error = "Key %s's value is out of range for column %s" % \
                        (key, column_name)
                    raise DataValidationFailed(error)

                # Now check ranges for values in dictionary

                # Skip range check for bools
                if type(data) is bool:
                    continue

                value = data

                min_ = column_data.valueRangeMin
                max_ = column_data.valueRangeMax

                # If kvs is defined, ranges shouldbe taken from it
                if column_data.kvs and key in column_data.kvs:
                    # Skip range check for booleans
                    if column_data.kvs[key]['type'] == ovs_types.BooleanType:
                        continue
                    else:
                        min_ = column_data.kvs[key]['rangeMin']
                        max_ = column_data.kvs[key]['rangeMax']

                    # If value is a string, it might represent values of other
                    # types and therefore it needs to be converted
                    if type(value) in ovs_types.StringType.python_types:
                        column_ovs_type = column_data.kvs[key]['type']
                        value = \
                            convert_string_to_value_by_type(value,
                                                            column_ovs_type)

                # If it was a string all along or if after convertion it's
                # still a string, its length range is checked instead
                if type(value) in ovs_types.StringType.python_types:
                    value = len(value)

                if (value < min_ or
                        value > max_):
                    error = "Dictionary value %s is out of range " % data + \
                        "for key %s in column %s" % (key, column_name)
                    raise DataValidationFailed(error)

    # Check single elements (non-list/non-dictionary)
    # Except boolean, as there's no range for them
    elif data_type not in ovs_types.BooleanType.python_types:

        # Exception: if column is not a list,
        # a single value list is accepted
        if data_type is list:
            value = request_data[0]
            data_type = type(value)
        else:
            value = request_data

        if data_type in ovs_types.StringType.python_types:
            value = len(value)

        if value < column_data.rangeMin or value > column_data.rangeMax:
            error = "Attribute value is out of range for column %s" % \
                column_name
            raise DataValidationFailed(error)


def _get_row_from_uri(uri, schema, idl):

    verified_resource = parse.parse_url_path(uri, schema, idl)
    if verified_resource is None:
        error = "Reference %s could not be identified" % uri
        raise DataValidationFailed(error)

    # get the Row instance of the reference we are adding
    while verified_resource.next is not None:
        verified_resource = verified_resource.next
    row = utils.get_row_from_resource(verified_resource, idl)
    return row


def verify_forward_reference(data, resource, schema, idl):
    """
    converts the forward reference URIs to corresponding Row references
    Parameters:
        data - post/put data
        resource - Resource object being accessed
        schema = restparser schema object
        idl - ovs.db.idl.Idl object
    """
    reference_keys = resource.keys[OVSDB_SCHEMA_REFERENCE]
    verified_references = {}

    # check for invalid keys
    for key in reference_keys:
        if key in data:
            category = reference_keys[key].category
            relation = reference_keys[key].relation

            if category != OVSDB_SCHEMA_CONFIG or \
                    relation == 'parent':
                        error = "Invalid reference: %s" % key
                        raise DataValidationFailed(error)

    for key in reference_keys:
        if key in data:
            # this is either a URI or list of URIs or dictionary
            table_schema = schema.ovs_tables[resource.table]
            kv_type = table_schema.references[key].kv_type
            _refdata = data[key]
            notList = False
            # Verify if input is of DictType
            if kv_type and not isinstance(_refdata, types.DictType):
                error = "Reference needs to be a dictionary %s" % key
                raise DataValidationFailed(error)

            if not isinstance(_refdata, types.ListType) and not kv_type:
                notList = True
                _refdata = [_refdata]

            # check range
            _min = reference_keys[key].n_min
            _max = reference_keys[key].n_max
            if len(_refdata) < _min or len(_refdata) > _max:
                error = "Reference list is out of range for key %s" % key
                raise DataValidationFailed(error)
            if kv_type:
                references = {}
                key_type = table_schema.references[key].kv_key_type.name
                # TODO: Support other types
                for k, v in _refdata.iteritems():
                    if key_type == INTEGER:
                        k = int(k)
                    row = _get_row_from_uri(v, schema, idl)
                    references.update({k:row})
            else:
                references = []
                for uri in _refdata:
                    row = _get_row_from_uri(uri, schema, idl)
                    references.append(row)
                    if notList:
                        references = references[0]

            verified_references[key] = references

    return verified_references


def verify_referenced_by(data, resource, schema, idl):
    '''
    subroutine to validate referenced_by uris/attribute JSON

    {
        "referenced_by": [
            {
                "uri": "URI1",
                "attributes": [
                    "a",
                    "b"
                ]
            },
            {
                "uri": "URI2"
            },
            {
                "uri": "URI3",
                "attributes":[]
            }
        ]
    }
    '''

    table = resource.table

    verified_referenced_by = {OVSDB_SCHEMA_REFERENCED_BY: []}
    for item in data:
        uri = item['uri']
        attributes = None

        if 'attributes' in item:
            attributes = item['attributes']

        # verify URI
        uri_resource = parse.parse_url_path(uri, schema, idl,
                                            REQUEST_TYPE_CREATE)

        if uri_resource is None:
            error = "referenced_by resource error"
            raise DataValidationFailed(error)

        # go to the last resource
        while uri_resource.next is not None:
            uri_resource = uri_resource.next

        if uri_resource.row is None:
            app_log.debug('uri: ' + uri + ' not found')
            error = "referenced_by resource error"
            raise DataValidationFailed(error)

        # attributes
        references = uri_resource.keys[OVSDB_SCHEMA_REFERENCE]
        reference_keys = references.keys()
        if attributes is not None and len(attributes) > 0:
            for attribute in attributes:
                if attribute not in reference_keys:
                    error = "Attribute %s not found" % attribute
                    raise DataValidationFailed(error)

                # check attribute is not a parent or child
                if references[attribute].relation is not 'reference':
                    error = "Attribute should be a reference"
                    raise DataValidationFailed(error)

        # if attribute list has only one element, make it a non-list to keep
        # it consistent with single attribute case (that need not be mentioned)
            if len(attributes) == 1:
                attributes = attributes[0]
        else:
            # find the lone attribute
            _found = False
            for key, value in references.iteritems():
                if value.ref_table == table:
                    if _found:
                        error = "multiple attributes possible, specify one"
                        raise DataValidationFailed(error)
                    else:
                        _found = True
                        attributes = key

        # found the uri and attributes
        uri_resource.column = attributes
        verified_referenced_by[OVSDB_SCHEMA_REFERENCED_BY].append(uri_resource)

    return verified_referenced_by


def find_unknown_attribute(data, config_keys, reference_keys):

    for column_name in data:
        if not (column_name in config_keys or
                column_name in reference_keys):
            return column_name

    return None


def get_non_mutable_attributes(resource, schema):
    config_keys = resource.keys[OVSDB_SCHEMA_CONFIG]
    reference_keys = resource.keys[OVSDB_SCHEMA_REFERENCE]

    attribute_keys = {}
    attribute_keys.update(config_keys)
    attribute_keys.update(reference_keys)

    result = []
    for key, column in attribute_keys.iteritems():
        if not column.mutable:
            result.append(key)

    return result
