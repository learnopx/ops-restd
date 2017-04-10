# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
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

from opsrest.resource import Resource
from opsrest.utils import utils
from opsrest.constants import *
import ovs.ovsuuid

import types
import json
import urllib

from tornado.log import app_log


def split_path(path):
    path = path.split('/')
    path = [urllib.unquote(i) for i in path if i != '']
    return path


def parse_url_path(path, schema, idl, http_method='GET'):

    if not path.startswith(REST_VERSION_PATH):
        app_log.debug("[parse_url_path]: path does not start with %s" %
                      REST_VERSION_PATH)
        return None

    # remove version and split path
    path = path[len(REST_VERSION_PATH):]
    path = split_path(path)
    if not path:
        app_log.debug("[parse_url_path]: path is empty")
        return None

    # we only serve URIs that begin with '/system'
    if path[0] != OVSDB_SCHEMA_SYSTEM_URI:
        app_log.debug("[parse_url_path]: path does not start with /%s" %
                      OVSDB_SCHEMA_SYSTEM_URI)
        return None

    resource = Resource(OVSDB_SCHEMA_SYSTEM_TABLE, schema)

    if resource.table not in idl.tables:
        app_log.debug("[parse_url_path]: resource table not in idl tables")
        return None

    if idl.tables[resource.table].rows.keys():
        resource.row = idl.tables[resource.table].rows.keys()[0]
    else:
        app_log.debug("[parse_url_path]: table has no rows")
        return None

    path = path[1:]
    if not path:
        return resource

    try:
        parse(path, resource, schema, idl, http_method)
        return resource
    except Exception as e:
        app_log.debug(str(e))
        app_log.debug('resource not found')
        return None

    app_log.debug("[parse_url_path]: default return")
    return None


def parse(path, resource, schema, idl, http_method):

    if not path:
        return None

    ovs_tables = schema.ovs_tables
    table_names = ovs_tables.keys()
    new_resource = None

    # check if path[0] is a forward referenced child of resource.table
    if path[0] in ovs_tables[resource.table].columns \
            and path[0] in ovs_tables[resource.table].children:

        resource.relation = OVSDB_SCHEMA_CHILD
        resource.column = path[0]
        _max = schema.ovs_tables[resource.table].references[resource.column].n_max
        app_log.debug("%s is a forward child in %s" % (path[0],
                      resource.table))

        child_table = ovs_tables[resource.table].references[resource.column].ref_table
        new_resource = Resource(child_table, schema)
        resource.next = new_resource

        # index columns
        indexes = ovs_tables[new_resource.table].indexes if \
                ovs_tables[new_resource.table].indexes[0] != 'uuid' else None
        path = path[1:]

        if not path and _max > 1:
            # done parsing uri
            return

        if _max == 1:
            parent = idl.tables[resource.table].rows[resource.row]
            child_row = parent.__getattr__(resource.column)
            if not child_row and path:
                raise Exception
            elif not child_row and not path:
                return
            elif isinstance(child_row, list):
                new_resource.row = child_row[0].uuid
            elif isinstance(child_row, dict):
                new_resource.row = child_row.values()[0].uuid
                new_resource.index = child_row.keys()[0]

        elif indexes:
            if len(path) < len(indexes):
                # not enough indices
                raise Exception

            index_list = path[0:len(indexes)]
            row = verify_index(new_resource, resource, index_list, schema, idl)
            if row is None:
                # row with index doesn't exist
                raise Exception

            new_resource.row = row.uuid
            new_resource.index = index_list
            path = path[len(index_list):]

        else:
            # children are either an ordered list or a dict
            parent = idl.tables[resource.table].rows[resource.row]
            children = parent.__getattr__(resource.column)
            if not children:
                raise Exception

            index = path[0]
            if isinstance(children, dict):
                column = schema.ovs_tables[resource.table].references[resource.column]
                key_type = column.kv_key_type.name
                if key_type  == 'integer':
                    index = int(index)
                elif key_type == 'uuid':
                    raise Exception
            else:
                # ordered list
                index = int(index)

            try:
                row = children[index]
                new_resource.row = row.uuid
                new_resource.index = index
                path = path[1:]
            except:
                # not found
                raise Exception

    # top-level reference or back referenced child
    elif path[0] in schema.plural_name_map:
        # check if path[0] is a back referenced child of resource.table
        path[0] = schema.plural_name_map[path[0]]
        if path[0] in ovs_tables[resource.table].children:
            resource.relation = OVSDB_SCHEMA_BACK_REFERENCE
            new_resource = Resource(path[0], schema)
            resource.next = new_resource
            app_log.debug("%s is a backward child in %s"
                          % (path[0], resource.table))

        # or if path[0] is a top level table
        elif resource.table == OVSDB_SCHEMA_SYSTEM_TABLE and \
                ovs_tables[path[0]].parent is None:
                    resource.relation = OVSDB_SCHEMA_TOP_LEVEL
                    new_resource = Resource(path[0], schema)
                    resource.next = new_resource
                    app_log.debug("%s is a top level table" % (path[0]))

        # do not proceed if relationship cannot be ascertained
        if not resource.relation:
            app_log.debug('URI not allowed: relationship does not exist')
            raise Exception

        indexes = ovs_tables[new_resource.table].indexes if \
                ovs_tables[new_resource.table].indexes[0] != 'uuid' else None
        path = path[1:]

        # done processing URI
        if not path:
            return
        # URI has an index to a resource
        elif indexes:

            if len(path) < len(indexes):
                raise Exception

            index_list = path[0:len(indexes)]
            row = verify_index(new_resource, resource, index_list, schema, idl)
            new_resource.row = row.uuid
            new_resource.index = index_list
            path = path[len(index_list):]

    if not new_resource:
        app_log.debug('URI not allowed: relationship does not exist')
        raise Exception

    app_log.debug("table: %s, row: %s, column: %s, relation: %s"
                  % (resource.table, str(resource.row),
                      str(resource.column), str(resource.relation)))

    # continue processing the path further
    parse(path, new_resource, schema, idl, http_method)


def verify_index(resource, parent, index_values, schema, idl):

    if resource.table not in idl.tables:
        return None

    if parent.relation == OVSDB_SCHEMA_BACK_REFERENCE:
        reference_keys = schema.ovs_tables[resource.table].references

        _refCol = None
        for key, value in reference_keys.iteritems():
            if (value.relation == OVSDB_SCHEMA_PARENT and
                    value.ref_table == parent.table):
                _refCol = key
                break

        if _refCol is None:
            return False

        dbtable = idl.tables[resource.table]
        row = utils.index_to_row(index_values, schema.ovs_tables[resource.table], dbtable)
        if row.__getattr__(_refCol).uuid == parent.row:
            return row
        else:
            return None

    elif parent.relation == OVSDB_SCHEMA_TOP_LEVEL:
        dbtable = idl.tables[resource.table]
        table_schema = schema.ovs_tables[resource.table]
        row = utils.index_to_row(index_values, table_schema, dbtable)
        return row

    else:
        # check if we are dealing with key/value type of forward reference
        kv_type = schema.ovs_tables[parent.table].references[parent.column].kv_type

        if kv_type:
            # check in parent table that the index exists
            app_log.debug('verifying key/value type reference')
            row = utils.kv_index_to_row(index_values, parent, idl)
        else:
            dbtable = idl.tables[resource.table]
            table_schema = schema.ovs_tables[resource.table]
            row = utils.index_to_row(index_values, table_schema, dbtable)
        return row
