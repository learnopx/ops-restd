#!/usr/bin/env python
# Copyright (C) 2015-2016 Hewlett-Packard Enterprise Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import getopt
import json
import os
import sys

from ovs.db import error
from ovs.db import types

from restparser import OVSReference
from restparser import normalizeName
from restparser import parseSchema

OP_GET_ALL = 0
OP_GET_ID = 1
OP_GET_OBJ = 2
OP_POST = 3
OP_PUT = 4
OP_PUT_OBJ = 5
OP_PATCH = 6
OP_DELETE = 7

DEFAULT_CUSTOM_OPS = [OP_GET_ALL, OP_GET_ID, OP_POST,
                      OP_PUT, OP_PATCH, OP_DELETE]


def addCommonResponse(responses):
    response = {}
    response["description"] = "Unauthorized"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["401"] = response

    response = {}
    response["description"] = "Forbidden"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["403"] = response

    response = {}
    response["description"] = "Not found"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["404"] = response

    response = {}
    response["description"] = "Method not allowed"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["405"] = response

    response = {}
    response["description"] = "Precondition failed"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["412"] = response

    response = {}
    response["description"] = "Internal server error"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["500"] = response

    response = {}
    response["description"] = "Service unavailable"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["503"] = response


def addGetResponse(responses):
    response = {}
    response["description"] = "Not modified"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["304"] = response

    response = {}
    response["description"] = "Not acceptable"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["406"] = response

    addCommonResponse(responses)


def addPostResponse(responses):
    response = {}
    response["description"] = "Created"
    schema = {}
    schema["$ref"] = "#/definitions/Resource"
    response["schema"] = schema
    responses["201"] = response

    response = {}
    response["description"] = "Bad request"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["400"] = response

    response = {}
    response["description"] = "Not acceptable"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["406"] = response

    response = {}
    response["description"] = "Unsupported media type"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["415"] = response

    addCommonResponse(responses)


def addPutResponse(responses):
    response = {}
    response["description"] = "OK"
    responses["200"] = response

    response = {}
    response["description"] = "Bad request"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["400"] = response

    response = {}
    response["description"] = "Not acceptable"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["406"] = response

    response = {}
    response["description"] = "Unsupported media type"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["415"] = response

    addCommonResponse(responses)


def addPatchResponse(responses):
    response = {}
    response["description"] = "OK"
    responses["200"] = response

    response = {}
    response["description"] = "Bad request"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["400"] = response

    response = {}
    response["description"] = "Not acceptable"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["406"] = response

    response = {}
    response["description"] = "Unsupported media type"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["415"] = response

    addCommonResponse(responses)


def addDeleteResponse(responses):
    response = {}
    response["description"] = "Resource deleted"
    responses["204"] = response

    addCommonResponse(responses)


#
# Pass in chain of parent resources on URI path
#
def genCoreParams(table, parent_plurality, parents, resource_name,
                  is_plural=True):
    depth = len(parent_plurality)
    plural = False

    params = []
    for level in range(depth):
        if parent_plurality[level]:
            param = {}
            param["name"] = "p"*(depth-level) + "id"
            param["in"] = "path"
            param["description"] = normalizeName(parents[level], plural) + \
                " id"
            param["required"] = True
            param["type"] = "string"
            params.append(param)

    if is_plural:
        param = {}
        param["name"] = "id"
        param["in"] = "path"
        param["description"] = normalizeName(resource_name, plural) + \
            " id"
        param["required"] = True
        param["type"] = "string"
        params.append(param)

    return params


def genGetParams(table, is_instance=False):
    params = []

    param = {}
    param["name"] = "If-None-Match"
    param["in"] = "header"
    param["description"] = ("entity-tag value for representation " +
                            "comparison (see RFC 7232 - Conditional " +
                            "Requests - section 3.2)")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "depth"
    param["in"] = "query"
    param["description"] = "maximum depth of subresources included in " + \
                           "result, where depth value can be between zero " + \
                           "and ten"
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    if not is_instance:

        param = {}
        param["name"] = "sort"
        param["in"] = "query"
        param["description"] = "comma separated list of columns to sort " + \
                               "results by, add a - (dash) at the " + \
                               "beginning to make sort descending"
        param["required"] = False
        param["type"] = "string"
        params.append(param)

        param = {}
        param["name"] = "offset"
        param["in"] = "query"
        param["description"] = "index of the first element from the result" + \
                               " list to be returned"
        param["required"] = False
        param["type"] = "integer"
        params.append(param)

        param = {}
        param["name"] = "limit"
        param["in"] = "query"
        param["description"] = "number of elements to return from offset"
        param["required"] = False
        param["type"] = "integer"
        params.append(param)

        param = {}
        param["name"] = "keys"
        param["in"] = "query"
        param["description"] = "comma separated list of keys to display " \
                               "from the result"
        param["required"] = False
        param["type"] = "string"
        params.append(param)

        columns = {}
        columns.update(table.config)
        columns.update(table.stats)
        columns.update(table.status)
        columns.update(table.references)

        for column, data in columns.iteritems():
            if isinstance(data, OVSReference) or not data.is_dict:
                param = {}
                param["name"] = column
                param["in"] = "query"
                param["description"] = "filter '%s' by specified value" \
                    % column
                param["required"] = False

                if data.type == types.IntegerType:
                    param["type"] = "integer"
                elif data.type == types.RealType:
                    param["type"] = "real"
                else:
                    param["type"] = "string"

                params.append(param)

    return params


def genGetResource(table, parent_plurality, parents, resource_name, is_plural):
    op = {}
    op["summary"] = "Get a list of resources"
    op["description"] = "Get a list of resources"
    op["tags"] = [table.name]

    params = genCoreParams(table, parent_plurality, parents,
                           resource_name, is_plural)

    get_params = genGetParams(table)
    if get_params:
        params.extend(get_params)

    if params:
        op["parameters"] = params

    responses = {}
    response = {}
    response["description"] = "OK"
    response["headers"] = {'ETag':
                           {'description':
                            ('The current entity-tag for the selected ' +
                             'representation (see RFC 7232 - Conditional ' +
                             'Requests - section 2.3)'),
                            'type': 'string'}}
    schema = {}
    schema["type"] = "array"
    item = {}
    item["description"] = "Resource URI"
    item["$ref"] = "#/definitions/Resource"
    schema["items"] = item
    schema["description"] = "A list of URIs"
    response["schema"] = schema
    responses["200"] = response

    addGetResponse(responses)
    op["responses"] = responses

    return op


def genPostResource(table, parent_plurality,
                    parents, resource_name, is_plural):
    op = {}
    op["summary"] = "Create a new resource instance"
    op["description"] = "Create a new resource instance"
    op["tags"] = [table.name]

    params = genCoreParams(table, parent_plurality, parents,
                           resource_name, is_plural)
    param = {}
    param["name"] = "data"
    param["in"] = "body"
    param["description"] = "data"
    param["required"] = True

    if table.parent is None:
        # For referenced resource
        param["schema"] = {'$ref': "#/definitions/"+table.name
                           + "ConfigReferenced"}
    else:
        param["schema"] = {'$ref': "#/definitions/"+table.name+"ConfigOnly"}

    params.append(param)
    op["parameters"] = params

    responses = {}
    addPostResponse(responses)
    op["responses"] = responses

    return op


def genGetInstance(table, parent_plurality, parents, resource_name, is_plural):
    if table.config or table.status or table.stats:
        op = {}
        op["summary"] = "Get a set of attributes"
        op["description"] = "Get a set of attributes"
        op["tags"] = [table.name]

        params = genCoreParams(table, parent_plurality, parents,
                               resource_name, is_plural)
        param = {}
        param["name"] = "selector"
        param["in"] = "query"
        param["description"] = "select from config, status or stats, \
                                default to all"
        param["required"] = False
        param["type"] = "string"
        params.append(param)

        get_params = genGetParams(table, True)
        if get_params:
            params.extend(get_params)

        op["parameters"] = params

        responses = {}
        response = {}
        response["description"] = "OK"
        response["headers"] = {'ETag':
                               {'description':
                                ('The current entity-tag for the selected ' +
                                 'representation (see RFC 7232 - ' +
                                 'Conditional Requests - section 2.3)'),
                                'type': 'string'}}
        response["schema"] = {'$ref': "#/definitions/"+table.name+"All"}
        responses["200"] = response

        addGetResponse(responses)
        op["responses"] = responses

        return op


def genPutInstance(table, parent_plurality, parents, resource_name, is_plural):
    if table.config:
        op = {}
        op["summary"] = "Update configuration"
        op["description"] = "Update configuration"
        op["tags"] = [table.name]

        params = genCoreParams(table, parent_plurality, parents,
                               resource_name, is_plural)
        param = {}
        param["name"] = "If-Match"
        param["in"] = "header"
        param["description"] = ("entity-tag value for representation " +
                                "comparison (see RFC 7232 - Conditional " +
                                "Requests - section 3.1)")
        param["required"] = False
        param["type"] = "string"
        params.append(param)

        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "configuration"
        param["required"] = True
        param["schema"] = {'$ref': "#/definitions/"+table.name+"ConfigOnly"}
        params.append(param)
        op["parameters"] = params

        responses = {}
        addPutResponse(responses)
        op["responses"] = responses

        return op


def genPatchInstance(table, parent_plurality, parents, resource_name,
                     is_plural):
    if table.config:
        op = {}
        op["summary"] = "Update configuration"
        op["description"] = "Update configuration"
        op["tags"] = [table.name]

        params = genCoreParams(table, parent_plurality, parents,
                               resource_name, is_plural)
        param = {}
        param["name"] = "If-Match"
        param["in"] = "header"
        param["description"] = ("entity-tag value for representation " +
                                "comparison (see RFC 7232 - Conditional " +
                                "Requests - section 3.1)")
        param["required"] = False
        param["type"] = "string"
        params.append(param)

        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "JSON PATCH operations as defined at RFC 6902"
        param["required"] = True
        schema = {}
        schema["type"] = "array"
        schema["items"] = {'$ref': "#/definitions/PatchDocument"}
        param["schema"] = schema
        params.append(param)
        op["parameters"] = params

        responses = {}
        addPatchResponse(responses)
        op["responses"] = responses

        return op


def genDelInstance(table, parent_plurality, parents, resource_name, is_plural):
    op = {}
    op["summary"] = "Delete a resource instance"
    op["description"] = "Delete a resource instance"
    op["tags"] = [table.name]

    params = genCoreParams(table, parent_plurality, parents,
                           resource_name, is_plural)
    param = {}
    param["name"] = "If-Match"
    param["in"] = "header"
    param["description"] = ("entity-tag value for representation " +
                            "comparison (see RFC 7232 - Conditional " +
                            "Requests - section 3.1)")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    if params:
        op["parameters"] = params

    responses = {}
    addDeleteResponse(responses)
    op["responses"] = responses

    return op


# Gets the correlated Swagger representation of primitive data types.
def getDataType(type):
    if type == types.IntegerType:
        return "integer"
    elif type == types.RealType:
        return "real"
    elif type == types.BooleanType:
        return "boolean"
    elif type == types.StringType:
        return "string"
    else:
        raise error.Error("Unexpected attribute type %s" % type)


# Generate definition for a given base type
def genBaseType(type, min, max, desc):

    if not desc:
        desc = ''

    item = {}
    item["type"] = getDataType(type)
    item["description"] = desc

    if type != types.BooleanType:
        if type == types.StringType:
            minStr = "minLength"
            maxStr = "maxLength"
        else:
            minStr = "minimum"
            maxStr = "maximum"

        if min is not None and min is not 0:
            item[minStr] = min
        if max is not None and max is not sys.maxint:
            item[maxStr] = max

    return item


def genBaseTypeList(type, desc):

    if not desc:
        desc = ''

    sub = {}
    sub["type"] = "array"
    sub["description"] = desc
    item = {}
    item["type"] = str(type)
    sub["items"] = item

    return sub


def get_ref_key_and_type(table_name, parent_table, schema):
    keyName = None
    keyname_type = None

    if parent_table:
        references = schema.ovs_tables[parent_table].references
        for col_ref_name, ref_table in references.iteritems():
            column_ovsref = references[col_ref_name]
            if str(ref_table.ref_table) == table_name:
                if hasattr(column_ovsref, 'keyname'):
                    keyName = column_ovsref.keyname
                    keyname_type = str(column_ovsref.type)
                else:
                    keyName = None
                break

    return keyName, keyname_type


# Generate definitions including "properties" and "required" for all columns.
# Tuples of "properties" dictionary and "required" array are returned.
def genAllColDefinition(cols, table_name, definitions,
                        table_parent=None, schema=None):
    properties = {}
    required = []

    keyName, keyname_type = get_ref_key_and_type(table_name, table_parent,
                                                 schema)
    for colName, col in cols:
        properties[colName] = genDefinition(table_name, col, definitions)
        if keyName:
            properties[keyName] = {'type': keyname_type,
                                   'description': 'Forward reference key'}
            required.append(keyName)

        if not col.is_optional:
            required.append(col.name)

    return properties, required


# Generate definition for a column in a table
def genDefinition(table_name, col, definitions):
    properties = {}
    if col.is_dict and col.enum:
        # Key-Value type
        for key in col.enum:
            definition = {}
            # keys specified in schema file are all of string type
            definition["type"] = "string"
            properties[key] = definition

    if col.kvs:
        for key, detail in col.kvs.iteritems():
            if 'type' in detail.keys():
                type = detail['type']
            else:
                type = col.type
            if 'rangeMin' in detail.keys():
                min = detail['rangeMin']
            else:
                min = col.rangeMin
            if 'rangeMax' in detail.keys():
                max = detail['rangeMax']
            else:
                max = col.rangeMax
            if 'desc' in detail.keys():
                # TODO strip detail['desc'] from markdown tags
                desc = detail['desc']
            else:
                desc = ""
            properties[key] = genBaseType(type, min, max, desc)

    if not properties and col.is_dict:
        # Some maps in the schema do not have keys defined (i.e. external_ids).
        # If keys are not defined, the type of the key (i.e. "string") should
        # be rendered as the key, and the type of the value (i.e. "string")
        # should be rendered as the value.
        key_type = getDataType(col.type)
        properties[key_type] = genBaseType(col.value_type,
                                           col.valueRangeMin,
                                           col.valueRangeMax,
                                           "Key-Value pair for " + col.name)

    if properties:
        definitions[table_name + "-" + col.name + "-KV"] = {"properties":
                                                            properties}

        sub = {}
        sub["$ref"] = "#/definitions/" + table_name + "-" + col.name + "-KV"
        sub["description"] = "Key-Value pairs for " + col.name
        return sub
    elif col.is_list:
        # TODO strip col.desc from markdown tags
        return genBaseTypeList(col.type, col.desc)
    else:
        # simple attributes
        # TODO strip col.desc from markdown tags
        return genBaseType(col.type, col.rangeMin, col.rangeMax, col.desc)


def refProperties(schema, table, col_name):
    child_name = table.references[col_name].ref_table
    child_table = schema.ovs_tables[child_name]

    sub = {}
    if table.references[col_name].is_plural:
        sub["type"] = "array"
        sub["description"] = "A list of " + child_table.name \
                             + " references"
        item = {}
        item["$ref"] = "#/definitions/Resource"
        sub["items"] = item
    else:
        sub["$ref"] = "#/definitions/Resource"
        sub["description"] = "Reference of " + child_table.name

    return sub


def getDefinition(schema, table, definitions):
    properties_config, required = genAllColDefinition(table.config.iteritems(),
                                                      table.name, definitions,
                                                      table.parent, schema)
    properties_full = copy.deepcopy(properties_config)

    # References are included in configuration if and only if they belong
    # to configuration category.
    for col_name in table.references:
        if table.references[col_name].category == "status":
            continue
        if table.references[col_name].relation == "reference":
            sub = refProperties(schema, table, col_name)
            properties_config[col_name] = sub
            properties_full[col_name] = sub

    definitions[table.name + "Config"] = {"properties": properties_config,
                                          "required": required}

    # Construct full configuration definition to include subresources
    for col_name in table.children:
        if col_name in table.references:
            if table.references[col_name].category == "status":
                continue
            else:
                # regular references
                subtable_name = table.references[col_name].ref_table
        else:
            # child added by parent relationship
            subtable_name = col_name

        sub = {}
        sub["$ref"] = "#/definitions/" + subtable_name + "ConfigData"
        sub["description"] = "Referenced resource of " + subtable_name + \
                             " instances"
        properties_full[col_name] = sub

        sub = {}
        sub["type"] = "array"
        sub["description"] = "A list of " + subtable_name \
                             + " references"
        item = {}
        item["$ref"] = "#/definitions/Resource"
        sub["items"] = item
        properties_config[col_name] = sub

    # Special treat /system resource
    # Include referenced resources at the top level as children
    if table.name is "System":
        for subtable_name, subtable in schema.ovs_tables.iteritems():
            # Skipping those that are not top-level resources
            if subtable.parent is not None:
                continue
            # Skipping those that are not referenced
            if subtable_name not in schema.reference_map.values():
                continue

            sub = {}
            sub["$ref"] = "#/definitions/" + subtable.name + "ConfigData"
            sub["description"] = "Referenced resource of " + subtable.name + \
                                 " instances"
            properties_full[subtable_name] = sub

    definitions[table.name + "ConfigFull"] = {"properties": properties_full,
                                              "required": required}

    properties = {}
    definition = {}
    required = []
    definition["type"] = "string"
    definition["description"] = table.name + " id"
    config = "id"
    required.append(config)
    properties[config] = definition
    definition = {}
    definition["$ref"] = "#/definitions/" + table.name + "ConfigFull"
    definition["description"] = "Configuration of " + table.name + " instance"
    config = "configuration"
    required.append(config)
    properties[config] = definition

    definitions[table.name + "ConfigInstance"] = {"properties": properties,
                                                  "required": required}

    properties = {}
    sub = {}
    if table.is_many:
        sub["type"] = "array"
        sub["description"] = "A list of " + table.name + " instances"
        item = {}
        item["$ref"] = "#/definitions/" + table.name + "ConfigInstance"
        sub["items"] = item
    else:
        sub["$ref"] = "#/definitions/" + table.name + "ConfigFull"
        sub["description"] = "Configuration of " + table.name
    properties[table.name] = sub

    definitions[table.name + "ConfigData"] = {"properties": properties}

    properties, required = genAllColDefinition(table.status.iteritems(),
                                               table.name, definitions)

    for col_name in table.references:
        if table.references[col_name].category == "status":
            sub = refProperties(schema, table, col_name)
            properties[col_name] = sub

    definitions[table.name + "Status"] = {"properties": properties,
                                          "required": required}

    properties, required = genAllColDefinition(table.stats.iteritems(),
                                               table.name, definitions)
    definitions[table.name + "Stats"] = {"properties": properties,
                                         "required": required}

    properties = {}
    sub = {}
    sub["$ref"] = "#/definitions/" + table.name + "Config"
    sub["description"] = "Configuration of " + table.name
    properties["configuration"] = sub
    sub = {}
    sub["$ref"] = "#/definitions/" + table.name + "Status"
    sub["description"] = "Status of " + table.name
    properties["status"] = sub
    sub = {}
    sub["$ref"] = "#/definitions/" + table.name + "Stats"
    sub["description"] = "Statistics of " + table.name
    properties["statistics"] = sub

    definitions[table.name + "All"] = {"properties": properties}

    properties = {}
    sub = {}
    required = []
    sub["$ref"] = "#/definitions/" + table.name + "Config"
    sub["description"] = "Configuration of " + table.name
    config = "configuration"
    required.append(config)
    properties[config] = sub

    definitions[table.name + "ConfigOnly"] = {"properties": properties,
                                              "required": required}

    properties = {}
    sub = {}
    required = []
    sub["$ref"] = "#/definitions/" + table.name + "Config"
    sub["description"] = "Configuration of " + table.name
    config = "configuration"
    required.append(config)
    properties[config] = sub

    sub = {}
    sub["type"] = "array"
    sub["description"] = "A list of reference points"
    item = {}
    item["$ref"] = "#/definitions/ReferencedBy"
    sub["items"] = item
    config = "referenced_by"
    required.append(config)
    properties[config] = sub

    definitions[table.name + "ConfigReferenced"] = {"properties": properties,
                                                    "required": required}


def genPatchDefinition(definitions):
    patch_op = {}
    patch_op["type"] = 'string'
    patch_op["description"] = "PATCH operation to be performed."
    patch_op["enum"] = ["add", "remove", "replace", "move", "copy", "test"]

    patch_path = {}
    patch_path["type"] = "string"
    patch_path["description"] = "A JSON Pointer. "\
        "Target location where the operation is performed."

    patch_value = {}
    patch_value["type"] = "object"
    patch_value["description"] = "The value to be used within the operations."

    patch_from = {}
    patch_from["type"] = "string"
    patch_from["description"] = "A JSON Pointer. "\
        "Target location where the operation is performed."

    properties = {"op": patch_op,
                  "path": patch_path,
                  "value": patch_value,
                  "from": patch_from
                  }
    description = "JSON Patch document (RFC 6902)."
    definitions["PatchDocument"] = {"properties": properties,
                                    "required": ["op", "path"],
                                    "description": description}


def genAPI(paths, definitions, schema, table, resource_name, parent,
           parents, parent_plurality):
    prefix = "/system"
    depth = len(parents)
    for index, ancestor in enumerate(parents):
        prefix = prefix + "/" + ancestor
        if parent_plurality[index]:
            idname = "{" + "p"*(depth - index) + "id}"
            prefix = prefix + "/" + idname

    # Parentless resources always have multiple instances
    if resource_name is None:
        # system table
        is_plural = False
    elif parent is None:
        is_plural = True
    elif resource_name not in parent.references:
        # parent relation always have multiple children
        is_plural = True
    else:
        is_plural = parent.references[resource_name].is_plural

    if resource_name is not None:
        path = prefix + "/" + resource_name
    else:
        path = prefix

    ops = {}
    if is_plural:
        op = genGetResource(table, parent_plurality, parents,
                            resource_name, False)
        if op is not None:
            ops["get"] = op
        op = genPostResource(table, parent_plurality, parents,
                             resource_name, False)
        if op is not None:
            ops["post"] = op
    else:
        op = genGetInstance(table, parent_plurality, parents,
                            resource_name, is_plural)
        if op is not None:
            ops["get"] = op

        op = genPutInstance(table, parent_plurality, parents,
                            resource_name, is_plural)
        if op is not None:
            ops["put"] = op

        op = genPatchInstance(table, parent_plurality, parents,
                              resource_name, is_plural)
        if op is not None:
            ops["patch"] = op

    paths[path] = ops

    if is_plural:
        path = path + "/{id}"
        ops = {}
        op = genGetInstance(table, parent_plurality, parents,
                            resource_name, is_plural)
        if op is not None:
            ops["get"] = op

        op = genPutInstance(table, parent_plurality, parents,
                            resource_name, is_plural)
        if op is not None:
            ops["put"] = op

        op = genPatchInstance(table, parent_plurality, parents,
                              resource_name, is_plural)
        if op is not None:
            ops["patch"] = op

        op = genDelInstance(table, parent_plurality, parents,
                            resource_name, is_plural)
        if op is not None:
            ops["delete"] = op

        paths[path] = ops

    getDefinition(schema, table, definitions)

    # Stop for system resource
    if resource_name is None:
        return

    # Recursive into next level resources
    for col_name in table.references:
        child_name = table.references[col_name].ref_table
        child_table = schema.ovs_tables[child_name]
        if col_name in table.children:
            # True child resources
            parents.append(resource_name)
            parent_plurality.append(is_plural)
            genAPI(paths, definitions, schema, child_table, col_name,
                   table, parents, parent_plurality)
            parents.pop()
            parent_plurality.pop()
        elif table.references[col_name].relation == "parent":
            continue
        else:
            # Referenced resources (no operation exposed)
            continue

    # For child resources declared with "parent" relationship
    for col_name in table.children:
        if col_name in table.references:
            # Processed already
            continue

        # Use plural form of the resource name in URI
        child_table = schema.ovs_tables[col_name]
        child_name = normalizeName(col_name)
        parents.append(resource_name)
        parent_plurality.append(is_plural)
        genAPI(paths, definitions, schema, child_table, child_name,
               table, parents, parent_plurality)
        parents.pop()
        parent_plurality.pop()


def genCustomDef(resource_name, definitions):
    '''
    Creates the custom definition from a json schema file
    '''
    # Read custom json schema
    # TODO Find a way to read the json custom schemas from rest
    schema_path = os.path.join(os.path.dirname("../opsrest/custom/"),
                               'schemas/%s.json' % resource_name)
    json_schema = None
    with open(schema_path, 'r') as data_file:
        json_schema = json.load(data_file)

    # Create swagger definitions structure
    # Step 3: Create ResourceConfig, ResourceStatus, ResourceStats definitions
    if json_schema:
        properties_config = json_schema["properties"]["configuration"]
        if "properties" in properties_config:
            definitions[resource_name + "Config"] = properties_config
        else:
            definitions[resource_name + "Config"] = {"configuration": {}}

        properties_status = json_schema["properties"]["status"]
        if "properties" in properties_status:
            definitions[resource_name + "Status"] = properties_status
        else:
            definitions[resource_name + "Status"] = {"status": {}}

        properties_stats = json_schema["properties"]["statistics"]
        if "properties" in properties_status:
            definitions[resource_name + "Stats"] = properties_stats
        else:
            definitions[resource_name + "Stats"] = {"statistics": {}}
    else:
        definitions[resource_name + "Config"] = {"properties": {}}
        definitions[resource_name + "Status"] = {"properties": {}}
        definitions[resource_name + "Stats"] = {"properties": {}}

    # Step 2: Create ResourceConfigAll definition
    properties = {}
    sub = {}
    sub["$ref"] = "#/definitions/" + resource_name + "Config"
    sub["description"] = "Configuration of " + resource_name
    properties["configuration"] = sub
    sub = {}
    sub["$ref"] = "#/definitions/" + resource_name + "Status"
    sub["description"] = "Status of " + resource_name
    properties["status"] = sub
    sub = {}
    sub["$ref"] = "#/definitions/" + resource_name + "Stats"
    sub["description"] = "Statistics of " + resource_name
    properties["statistics"] = sub
    definitions[resource_name + "All"] = {"properties": properties,
                                          "required": ["configuration"]}

    # Step 3: Create ResourceConfigOnly definition
    properties = {}
    sub = {}
    sub["$ref"] = "#/definitions/" + resource_name + "Config"
    sub["description"] = "Configuration of " + resource_name
    properties["configuration"] = sub
    definitions[resource_name + "ConfigOnly"] = {"properties": properties,
                                                 "required": ["configuration"]}

    properties = {}
    sub = {}
    sub["$ref"] = "#/definitions/" + resource_name + "Status"
    sub["description"] = "Status of " + resource_name
    properties["status"] = sub

    definitions[resource_name + "StatusOnly"] = {"properties": properties,
                                                 "required": ["status"]}


def genCustomAPI(resource_name, path, paths,
                 operations=DEFAULT_CUSTOM_OPS, get_only='All'):
    '''
    Creates Custom Resource API
    '''
    ops_id = {}
    ops = {}
    if OP_GET_ALL in operations:
        # Get All Operation
        op = {}
        op["summary"] = "Get a list of resources"
        op["description"] = "Get a list of resources"
        op["tags"] = [resource_name]

        params = []
        op["parameters"] = params

        responses = {}
        response = {}
        response["description"] = "OK"
        schema = {}
        schema["type"] = "array"
        item = {}
        item["description"] = "Resource URI"
        item["$ref"] = "#/definitions/Resource"
        schema["items"] = item
        schema["description"] = "A list of URIs"
        response["schema"] = schema
        responses["200"] = response

        addGetResponse(responses)
        op["responses"] = responses
        ops["get"] = op

    if OP_GET_ID in operations:
        # Get by id Operation
        op = {}
        op["summary"] = "Get a set of attributes"
        op["description"] = "Get a set of attributes"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "id"
        param["in"] = "path"
        param["description"] = resource_name + " id"
        param["required"] = True
        param["type"] = "string"
        params.append(param)
        op["parameters"] = params

        responses = {}
        response = {}
        response["description"] = "OK"
        response["schema"] = {'$ref': "#/definitions/" +
                              resource_name + get_only}
        responses["200"] = response

        addGetResponse(responses)
        op["responses"] = responses
        ops_id["get"] = op

    if OP_GET_OBJ in operations:
        # Get object Operation
        op = {}
        op["summary"] = "Get a set of attributes"
        op["description"] = "Get a set of attributes"
        op["tags"] = [resource_name]

        params = []
        op["parameters"] = params
        responses = {}
        response = {}
        response["description"] = "OK"
        response["schema"] = {'$ref': "#/definitions/" +
                              resource_name + get_only}
        responses["200"] = response

        addGetResponse(responses)
        op["responses"] = responses
        ops["get"] = op

    if OP_POST in operations:
        # Post Operation
        op = {}
        op["summary"] = "Create a new resource instance"
        op["description"] = "Create a new resource instance"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "data"
        param["required"] = True
        param["schema"] = {'$ref': "#/definitions/" +
                           resource_name + "ConfigOnly"}
        params.append(param)
        op["parameters"] = params

        responses = {}
        addPostResponse(responses)
        op["responses"] = responses
        ops["post"] = op

    if OP_PUT in operations:
        # Update Operation
        op = {}
        op["summary"] = "Update configuration"
        op["description"] = "Update configuration"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "id"
        param["in"] = "path"
        param["description"] = resource_name + " id"
        param["required"] = True
        param["type"] = "string"
        params.append(param)

        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "configuration"
        param["required"] = True
        param["schema"] = {'$ref': "#/definitions/" +
                           resource_name + "ConfigOnly"}
        params.append(param)
        op["parameters"] = params

        responses = {}
        addPutResponse(responses)
        op["responses"] = responses
        ops_id["put"] = op

    if OP_PUT_OBJ in operations:
        # Update Operation
        op = {}
        op["summary"] = "Update configuration"
        op["description"] = "Update configuration"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "configuration"
        param["required"] = True
        param["schema"] = {'$ref': "#/definitions/" +
                           resource_name + "ConfigOnly"}
        params.append(param)
        op["parameters"] = params

        responses = {}
        addPutResponse(responses)
        op["responses"] = responses
        ops["put"] = op

    if OP_PATCH in operations:
        # Update Operation
        op = {}
        op["summary"] = "Update configuration"
        op["description"] = "Update configuration using JSON PATCH " + \
                            "Specification"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "id"
        param["in"] = "path"
        param["description"] = resource_name + " id"
        param["required"] = True
        param["type"] = "string"
        params.append(param)

        param = {}
        param["name"] = "data"
        param["in"] = "body"
        param["description"] = "JSON PATCH operations as defined at RFC 6902"
        param["required"] = True
        schema = {}
        schema["type"] = "array"
        schema["items"] = {'$ref': "#/definitions/PatchDocument"}
        param["schema"] = schema

        params.append(param)
        op["parameters"] = params

        responses = {}
        addPutResponse(responses)
        op["responses"] = responses
        ops_id["patch"] = op

    if OP_DELETE in operations:
        # Delete Operation
        op = {}
        op["summary"] = "Delete a resource instance"
        op["description"] = "Delete a resource instance"
        op["tags"] = [resource_name]

        params = []
        param = {}
        param["name"] = "id"
        param["in"] = "path"
        param["description"] = resource_name + " id"
        param["required"] = True
        param["type"] = "string"
        params.append(param)
        op["parameters"] = params

        responses = {}
        addDeleteResponse(responses)
        op["responses"] = responses
        ops_id["delete"] = op

    if ops_id:
        path_id = path + "/{id}"
        paths[path_id] = ops_id
    if ops:
        paths[path] = ops


def getFullConfigDef(schema, definitions):
    properties = {}
    definitions["FullConfig"] = {"properties": properties}


def genFullConfigAPI(paths):
    path = "/system/full-configuration"

    ops = {}
    op = {}
    op["summary"] = "Get full declarative configuration"
    op["description"] = "Fetch full declarative configuration"
    op["tags"] = ["FullConfiguration"]

    params = []
    param = {}
    param["name"] = "type"
    param["in"] = "query"
    param["description"] = "select from running or startup, \
                            default to running"
    param["required"] = False
    param["type"] = "string"
    params.append(param)
    op["parameters"] = params

    responses = {}
    response = {}
    response["description"] = "OK"
    response["schema"] = {'$ref': "#/definitions/SystemConfigFull"}
    responses["200"] = response

    addGetResponse(responses)
    op["responses"] = responses

    ops["get"] = op

    op = {}
    op["summary"] = "Update full declarative configuration"
    op["description"] = "Update full declarative configuration"
    op["tags"] = ["FullConfiguration"]

    params = []
    param = {}
    param["name"] = "type"
    param["in"] = "query"
    param["description"] = "select from running or startup, \
                            default to running"
    param["required"] = False
    param["type"] = "string"
    params.append(param)
    param = {}
    param["name"] = "data"
    param["in"] = "body"
    param["description"] = "declarative configuration"
    param["required"] = True
    param["schema"] = {'$ref': "#/definitions/SystemConfigFull"}
    params.append(param)

    op["parameters"] = params

    responses = {}
    addPutResponse(responses)
    op["responses"] = responses

    ops["put"] = op

    op = {}
    op["summary"] = "Update full declarative configuration"
    op["description"] = "Update full declarative configuration"
    op["tags"] = ["FullConfiguration"]

    params = []
    param = {}
    param["name"] = "type"
    param["in"] = "query"
    param["description"] = "select from running or startup, \
                            default to running"
    param["required"] = False
    param["type"] = "string"
    params.append(param)
    param = {}
    param["name"] = "data"
    param["in"] = "body"
    param["description"] = "declarative configuration"
    param["required"] = True
    param["schema"] = {'$ref': "#/definitions/SystemConfigFull"}
    params.append(param)

    op["parameters"] = params

    responses = {}
    addPatchResponse(responses)
    op["responses"] = responses

    ops["patch"] = op

    paths[path] = ops


def genUserLogin(paths):
    path = "/login"

    ops = {}
    op = {}
    op["summary"] = "User login"
    op["description"] = "Use username and password to log user in"
    op["tags"] = ["User"]

    params = []
    param = {}
    param["name"] = "username"
    param["in"] = "query"
    param["description"] = "User name"
    param["required"] = True
    param["type"] = "string"
    params.append(param)
    param = {}
    param["name"] = "password"
    param["in"] = "query"
    param["description"] = "Password"
    param["required"] = True
    param["type"] = "string"
    params.append(param)

    op["parameters"] = params

    responses = {}
    response = {}
    response["description"] = "User logged in, cookie set"
    responses["201"] = response

    response = {}
    response["description"] = "Bad request"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["400"] = response

    op["responses"] = responses

    ops["post"] = op

    paths[path] = ops


def genUserLogout(paths):
    path = "/logout"

    ops = {}
    op = {}
    op["summary"] = "User logout"
    op["description"] = "Log user out of the system"
    op["tags"] = ["User"]

    params = []

    op["parameters"] = params

    responses = {}
    response = {}
    response["description"] = "User logged out successfully, cookie removed"
    responses["200"] = response

    response = {}
    response["description"] = "Bad request"
    response["schema"] = {'$ref': "#/definitions/Error"}
    responses["400"] = response

    response = {}
    response["description"] = "User not authenticated"
    responses["401"] = response

    op["responses"] = responses

    ops["post"] = op

    paths[path] = ops


def genLogsAPI(paths, definitions):
    path = "/logs"
    ops = {}
    op = {}
    op["summary"] = "Log entries"
    op["description"] = "Get log entries"
    op["tags"] = ["Logs"]

    params = []
    param = {}
    param["name"] = "priority"
    param["in"] = "query"
    param["description"] = "Log priority levels. Valid values 0-7."
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "after-cursor"
    param["in"] = "query"
    param["description"] = ("Cursor string from the previous response " +
                            "last log entry.")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "since"
    param["in"] = "query"
    param["description"] = ("Fetch logs since the time specified. " +
                            "Valid format: YYYY-MM-DD hh:mm:ss. " +
                            "Relative words like yesterday, today, now," +
                            "1 day ago, 10 hours ago, 12 minutes ago are " +
                            "accepted. Words like hour ago, minute ago " +
                            "and day ago must precede with a positive " +
                            "integer and can be in plural form too.")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "until"
    param["in"] = "query"
    param["description"] = ("Fetch logs until the time specified. " +
                            "Valid format: YYYY-MM-DD hh:mm:ss. " +
                            "Relative words like yesterday, today, now," +
                            "1 day ago, 10 hours ago, 12 minutes ago are " +
                            "accepted. Words like hour ago, minute ago " +
                            "and day ago must precede with a positive " +
                            "integer and can be in plural form too.")
    param["required"] = False
    param["type"] = "string"
    params.append(param)
    param = {}
    param["name"] = "offset"
    param["in"] = "query"
    param["description"] = ("Offset is the starting log entry, starts " +
                            "with 0. Offset will be the previous " +
                            "offset + limit on the next request.")
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "limit"
    param["in"] = "query"
    param["description"] = ("Number of log entries in the response." +
                            "Valid range is 1-1000")
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "MESSAGE"
    param["in"] = "query"
    param["description"] = "Exact log message that is expected to be matched."
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "MESSAGE_ID"
    param["in"] = "query"
    param["description"] = ("A 128-bit message identifier for recognizing " +
                            "certain message types. All openswitch events " +
                            "are stored with the message ID " +
                            "50c0fa81c2a545ec982a54293f1b1945 in the " +
                            "systemd journal. Use this MESSAGE_ID to " +
                            "query all of the OPS events.")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "PRIORITY"
    param["in"] = "query"
    param["description"] = "Log priority level."
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "SYSLOG_IDENTIFIER"
    param["in"] = "query"
    param["description"] = ("This is the module generating the log message. " +
                            "Use this field to filter logs by a specific " +
                            "module.")
    param["required"] = False
    param["type"] = "string"
    params.append(param)

    param = {}
    param["name"] = "_PID"
    param["in"] = "query"
    param["description"] = ("The Process ID of the process that is " +
                            "generating the log entry.")
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "_GID"
    param["in"] = "query"
    param["description"] = ("The Group ID of the process that is " +
                            "generating the log entry.")
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    param = {}
    param["name"] = "_UID"
    param["in"] = "query"
    param["description"] = ("The User ID of the process that is " +
                            "generating the log entry.")
    param["required"] = False
    param["type"] = "integer"
    params.append(param)

    op["parameters"] = params

    responses = {}
    response = {}
    schema = {}
    schema["type"] = "array"
    item = {}
    item["description"] = "List of log entries"
    item["$ref"] = "#/definitions/LogEntry"
    schema["items"] = item
    schema["description"] = "A list of KV pairs"

    response["description"] = "Get a list of log entries"
    response["schema"] = schema
    responses["200"] = response
    addGetResponse(responses)
    op["responses"] = responses

    ops["get"] = op
    paths[path] = ops
    # Generate logs definitions
    item = {}
    properties = {}
    item["type"] = "string"
    item["description"] = "Key-Value pairs for log entry"
    properties["string"] = item
    definitions["LogEntry"] = {"properties": properties}


def getFullAPI(schema):
    api = {}
    api["swagger"] = "2.0"

    info = {}
    info["title"] = "OpenSwitch REST API"
    info["description"] = "REST interface for management plane"
    info["version"] = "1.0.0"
    api["info"] = info

    # by default, the REST implementation runs on the same host
    # at the same port as the Swagger UI
    api["host"] = ""
    # Should be changed to use https instead
    api["schemes"] = ["https"]
    api["basePath"] = "/rest/v1"
    api["produces"] = ["application/json"]

    paths = {}
    definitions = {}
    genPatchDefinition(definitions)

    # Special treat /system resource
    systemTable = schema.ovs_tables["System"]
    parents = []
    parent_plurality = []
    genAPI(paths, definitions, schema, systemTable, None, None,
           parents, parent_plurality)

    # Top-level tables exposed in system table
    for col_name in systemTable.references:
        name = systemTable.references[col_name].ref_table
        table = schema.ovs_tables[name]

        if col_name in systemTable.children:
            # True child resources
            parents = []
            parent_plurality = []
            genAPI(paths, definitions, schema, table, col_name,
                   systemTable, parents, parent_plurality)
        else:
            # Referenced resources (no operation exposed)
            continue

    # Put referenced resources at the top level
    for table_name, table in schema.ovs_tables.iteritems():
        # Skipping those that are not top-level resources
        if table.parent is not None:
            continue
        if table_name is "System":
            continue

        parents = []
        parent_plurality = []
        # Use plural form of the resource name in the URI
        genAPI(paths, definitions, schema, table, table.plural_name,
               None, parents, parent_plurality)

    # Creating the access URL for declarative configuration manipulation
    genFullConfigAPI(paths)

    # Creating the login URL
    genUserLogin(paths)

    # Creating the logout URL
    genUserLogout(paths)

    # Creating the logs URL
    genLogsAPI(paths, definitions)

    # Custom APIs
    genCustomDef("Account", definitions)
    genCustomAPI("Account", "/account", paths,
                 [OP_GET_OBJ, OP_PUT_OBJ], get_only='StatusOnly')

    api["paths"] = paths

    properties = {}
    properties["message"] = {"type": "string"}
    definitions["Error"] = {"properties": properties}

    definition = {}
    definition["type"] = "string"
    definition["description"] = "Resource URI"
    definitions["Resource"] = definition

    properties = {}
    definition = {}
    definition["type"] = "string"
    definition["description"] = "URI of the resource making the reference"
    properties["uri"] = definition
    definition = {}
    definition["type"] = "array"
    definition["description"] = "A list of reference points, \
                                 can be empty for default"
    items = {}
    items["type"] = "string"
    definition["items"] = items
    properties["attributes"] = definition
    definitions["ReferencedBy"] = {"properties": properties}

    api["definitions"] = definitions

    return api


def docGen(schemaFile, title=None, version=None):
    schema = parseSchema(schemaFile, loadDescription=True)

    # Special treat System table as /system resource
    schema.ovs_tables["System"] = schema.ovs_tables.pop("System")
    schema.ovs_tables["System"].name = "System"

    api = getFullAPI(schema)
    return json.dumps(api, sort_keys=True, indent=4)


def usage():
    print """\
%(argv0)s: REST API documentation generator
Parse the meta schema file based on OVSDB schema to
generate REST API YAML file for rendering through swagger.
usage: %(argv0)s [OPTIONS] SCHEMA
where SCHEMA is an extended OVSDB schema in JSON format

The following options are also available:
  --title=TITLE               use TITLE as title instead of schema name
  --version=VERSION           use VERSION to override
  -h, --help                  display this help message\
""" % {'argv0': sys.argv[0]}
    sys.exit(0)


if __name__ == "__main__":

    try:
        try:
            options, args = getopt.gnu_getopt(sys.argv[1:], 'h',
                                              ['title=', 'version=', 'help'])
        except getopt.GetoptError, geo:
            sys.stderr.write("%s: %s\n" % (sys.argv[0], geo.msg))
            sys.exit(1)

        title = None
        version = None
        for key, value in options:
            if key == '--title':
                title = value
            elif key == '--version':
                version = value
            elif key in ['-h', '--help']:
                usage()
            else:
                sys.exit(0)

        if len(args) > 2:
            sys.stderr.write("Exactly 1 non-option arguments required "
                             "(use --help for help)\n")
            sys.exit(1)

        s = docGen(args[0], title, version)
        print s

    except error.Error, e:
        sys.stderr.write("%s\n" % e.msg)
        sys.exit(1)
    except Exception, e:
        sys.stderr.write("%s\n" % e)
        sys.exit(1)

# Local variables:
# mode: python
# End:
