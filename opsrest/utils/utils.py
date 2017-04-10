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

import ovs.db.idl
import ovs
import ovs.db.types as ovs_types
import types
import uuid
import re
import urllib

from opsrest.resource import Resource
from opsrest.constants import *
from opsvalidator import validator
from tornado.log import app_log
from opsrest.exceptions import DataValidationFailed
from tornado.options import options
from tornado import gen
from opslib.restparser import ON_DEMAND_FETCHED_TABLES


def get_row_from_resource(resource, idl):
    """
    using instance of Resource find the corresponding
    ovs.db.idl.Row instance(s)

    returns an instance of ovs.db.idl.Row or a list of
    ovs.db.idl.Row instances

    Parameters:
        resource - opsrest.resource.Resource instance
        idl - ovs.db.idl.Idl instance
    """

    if not isinstance(resource, Resource):
        return None

    elif resource.table is None or resource.row is None or idl is None:
        return None
    else:
        # resource.row can be a single UUID object or a list of UUID objects
        rows = resource.row
        if type(rows) is not types.ListType:
            return idl.tables[resource.table].rows[resource.row]
        else:
            rowlist = []
            for row in rows:
                rowlist.append(idl.tables[resource.table].rows[row])
            return rowlist


def get_column_data_from_resource(resource, idl):
    """
    return column data
    Parameters:
        resource - opsrest.resource.Resource instance
        idl - ovs.db.idl.Idl instance
    """
    if (resource.table is None or resource.row is None or
            resource.column is None or idl is None):
        return None

    row = idl.tables[resource.table].rows[resource.row]

    if type(str(resource.column)) is types.StringType:
        return row.__getattr__(resource.column)
    elif type(resource.column) is types.ListType:
        columns = []
        for item in resource.column:
            columns.append(row.__getattr__(item))
        return columns
    else:
        return None


def get_column_data_from_row(row, column):
    """
    return column data from row
    Parameters:
        row - ovs.db.idl.Row instance
        column - column name
    """
    if type(str(column)) is types.StringType:
        return row.__getattr__(column)
    elif type(column) is types.ListType:
        columns = []
        for item in column:
            columns.append(row.__getattr__(item))
        return columns
    else:
        return None


def check_resource(resource, idl):
    """
    using Resource and Idl instance return a tuple
    containing the corresponding ovs.db.idl.Row
    and column name

    Parameters:
        resource - opsrest.resource.Resource instance
        idl - ovs.db.idl.Idl instance
    """

    if not isinstance(resource, Resource):
        return None
    elif (resource.table is None or resource.row is None or
            resource.column is None):
        return None
    else:
        return (get_row_from_resource(resource, idl), resource.column)


def add_kv_reference(key, reference, resource, idl):
    """
    Adds a KV type Row reference to a column entry in the DB
    Parameters:
        key - a unique key identifier
        reference - Row reference to be added
        resource - opsrest.resource.Resource instance
                   to which (key:reference) is added
        idl - ovs.db.idl.Idl instance
    """
    row = idl.tables[resource.table].rows[resource.row]
    kv_references = get_column_data_from_row(row, resource.column)

    updated_kv_references = {}
    for k, v in kv_references.iteritems():
        updated_kv_references[k] = v

    updated_kv_references[key] = reference
    row.__setattr__(resource.column, updated_kv_references)
    return True


def add_reference(reference, resource, idl):
    """
    Adds a Row reference to a column entry in the DB
    Parameters:
        reference - ovs.db.idl.Row instance
        resource - opsrest.resource.Resource instance
                   that corresponds to an entry in DB
        idl - ovs.db.idl.Idl instance
    """

    (row, column) = check_resource(resource, idl)
    if row is None or column is None:
        return False

    reflist = get_column_data_from_row(row, column)

    # a list of Row elements
    if len(reflist) == 0 or isinstance(reflist[0], ovs.db.idl.Row):
        updated_list = []
        for item in reflist:
            updated_list.append(item)
        updated_list.append(reference)
        row.__setattr__(column, updated_list)
        return True

    # a list-of-list of Row elements
    elif type(reflist[0]) is types.ListType:
        for _reflist in reflist:
            updated_list = []
            for item in _reflist:
                updated_list.append(item)
            updated_list.append(reference)
            row.__setattr__(column, updated_list)
        return True

    return False


def delete_reference(resource, parent, schema, idl):
    """
    Delete a referenced resource from another
    Parameters:
        resource - Resource instance to be deleted
        parent - Resource instance from which resource
                 is deleted
        schema - ovsdb schema object
        idl - ovs.db.idl.Idl instance
    """
    # kv type reference
    ref = None
    if schema.ovs_tables[parent.table].references[parent.column].kv_type:
        app_log.debug('Deleting KV type reference')
        key = resource.index
        parent_row = idl.tables[parent.table].rows[parent.row]
        kv_references = get_column_data_from_row(parent_row, parent.column)
        updated_kv_references = {}
        for k, v in kv_references.iteritems():
            if k == key:
                ref = v
            else:
                updated_kv_references[k] = v

        parent_row.__setattr__(parent.column, updated_kv_references)
    else:
        # normal reference
        app_log.debug('Deleting normal reference')
        ref = get_row_from_resource(resource, idl)
        parent_row = get_row_from_resource(parent, idl)
        reflist = get_column_data_from_row(parent_row, parent.column)

        if reflist is None:
            app_log.debug('reference list is empty')
            return False

        updated_references = []
        for item in reflist:
            if item.uuid != ref.uuid:
                updated_references.append(item)

        parent_row.__setattr__(parent.column, updated_references)

    return ref


def delete_all_references(resource, schema, idl):
    """
    Delete all occurrences of reference for resource
    Parameters:
        resource - resource whose references are to be
                   deleted from the entire DB
        schema - ovsdb schema object
        idl = ovs.db.idl.Idl instance
    """
    row = get_row_from_resource(resource, idl)
    #We get the tables that reference the row to delete table
    tables_reference = schema.references_table_map[resource.table]
    #Get the table name and column list we is referenced
    for table_name, columns_list in tables_reference.iteritems():
        app_log.debug("Table %s" % table_name)
        app_log.debug("Column list %s" % columns_list)
        table_schema = schema.ovs_tables[table_name]
        #Iterate each row to see wich tuple has the reference
        for uuid, row_ref in idl.tables[table_name].rows.iteritems():
            #Iterate over each reference column and check if has the reference
            for column_name in columns_list:
                #get the referenced values
                reflist = get_column_data_from_row(row_ref, column_name)
                if reflist is not None:
                    if table_schema.references[column_name].kv_type:
                        reflist = reflist.values()
                    #delete the reference on that row and column
                    delete_row_reference(reflist, row, row_ref, column_name)

    return row

def delete_row_reference(reflist, row, row_ref, column):
    updated_list = []
    for item in reflist:
        if item.uuid != row.uuid:
            updated_list.append(item)
    row_ref.__setattr__(column, updated_list)


def setup_new_row_by_resource(resource, data, schema, txn, idl):
    if not isinstance(resource, Resource):
        return None

    config_keys = resource.keys[OVSDB_SCHEMA_CONFIG]
    reference_keys = resource.keys[OVSDB_SCHEMA_REFERENCE].keys()

    row = setup_new_row(resource.table, data, schema, txn, idl,
                        config_keys, reference_keys)

    if row:
        resource.row = row.uuid

    return row


# create a new row, populate it with data
def setup_new_row(table_name, data, schema, txn, idl,
                  cfg_keys=None, ref_keys=None):
    if table_name is None:
        return None

    row = txn.insert(idl.tables[table_name])

    # Add config items
    if cfg_keys is None:
        config_keys = schema.ovs_tables[table_name].config
    else:
        config_keys = cfg_keys

    set_config_fields(row, data, config_keys)

    # add reference iitems
    if ref_keys is None:
        reference_keys = schema.ovs_tables[table_name].references.keys()
    else:
        reference_keys = ref_keys

    set_reference_items(row, data, reference_keys)

    return row


#Update columns from a row
def update_row(resource, data, schema, txn, idl):
    #Verify if is a Resource instance
    if not isinstance(resource, Resource):
        return None

    if resource.table is None:
        return None

    #get the row that will be modified
    row = get_row_from_resource(resource, idl)

    #Update config items
    config_keys = resource.keys[OVSDB_SCHEMA_CONFIG]
    set_config_fields(row, data, config_keys)

    # add or modify reference items (Overwrite references)
    reference_keys = resource.keys[OVSDB_SCHEMA_REFERENCE].keys()
    set_reference_items(row, data, reference_keys)

    return row


# set each config data on each column
def set_config_fields(row, data, config_keys):
    for key in config_keys:
        if key in data:
            row.__setattr__(key, data[key])


def set_reference_items(row, data, reference_keys):
    """
    set reference/list of references as a column item
    Parameters:
        row - ovs.db.idl.Row object to which references are added
        data - verified data
        reference_keys - reference column names
    """
    for key in reference_keys:
        if key in data:
            if isinstance(data[key], ovs.db.idl.Row):
                reflist = data[key]
            elif type(data[key]) is types.ListType:
                reflist = []
                for item in data[key]:
                    reflist.append(item)
            else:
                reflist = {}
                for k, v in data[key].iteritems():
                    reflist.update({k: v})

            row.__setattr__(key, reflist)


def get_attribute_and_type(row, ovs_column):
    attribute = row.__getattr__(ovs_column.name)
    attribute_type = type(attribute)

    # Convert single element lists to scalar
    # if schema defines a max of 1 element
    if attribute_type is list and ovs_column.n_max == 1:
        if len(attribute) > 0:
            attribute = attribute[0]
        else:
            attribute = None

    value_type = ovs_column.type
    if attribute_type is dict:
        value_type = ovs_column.value_type

    return attribute, value_type


def row_ovs_column_to_json(row, ovs_column):
    attribute, value_type = get_attribute_and_type(row, ovs_column)
    return to_json(attribute, value_type)


def row_to_json(row, column_keys):

    data_json = {}
    for key, ovs_col in column_keys.iteritems():
        data_json[key] = row_ovs_column_to_json(row, ovs_col)

    return data_json


def get_empty_by_basic_type(data):
    type_ = type(data)

    # If data is already a type, just use it
    if type_ is type:
        type_ = data
    elif type_ is ovs_types.AtomicType:
        type_ = data

    if type_ is types.DictType:
        return {}

    elif type_ is types.ListType:
        return []

    elif type_ in ovs_types.StringType.python_types or \
            type_ is ovs_types.StringType:
        return ''

    elif type_ in ovs_types.IntegerType.python_types or \
            type_ is ovs_types.IntegerType:
        return 0

    elif type_ in ovs_types.RealType.python_types or \
            type_ is ovs_types.RealType:
        return 0.0

    elif type_ is types.BooleanType or \
            type_ is ovs_types.BooleanType:
        return False

    elif type_ is types.NoneType:
        return None

    else:
        return ''


def to_json(data, value_type=None):
    type_ = type(data)

    if type_ is types.DictType:
        return dict_to_json(data, value_type)

    elif type_ is types.ListType:
        return list_to_json(data, value_type)

    elif type_ in ovs_types.StringType.python_types:
        return str(data)

    elif (type_ in ovs_types.IntegerType.python_types or
            type_ in ovs_types.RealType.python_types):
        return data

    elif type_ is types.BooleanType:
        return data

    elif type_ is types.NoneType:
        return None

    elif type_ is uuid.UUID:
        return str(data)

    elif type_ is ovs.db.idl.Row:
        return str(data.uuid)

    else:
        return str(data)


def has_column_changed(json_data, data):
    json_type_ = type(json_data)
    type_ = type(data)

    if json_type_ != type_:
        return False

    if (type_ is types.DictType or
            type_ is types.ListType or
            type_ is types.NoneType or
            type_ is types.BooleanType or
            type_ in ovs_types.IntegerType.python_types or
            type_ in ovs_types.RealType.python_types):
        return json_data == data

    else:
        return json_data == str(data)


def to_json_error(message, code=None, fields=None):
    dictionary = {"code": code, "fields": fields, "message": message}

    return dict_to_json(dictionary)


def dict_to_json(data, value_type=None):
    if not data:
        return data

    data_json = {}
    for key, value in data.iteritems():
        type_ = type(value)

        if isinstance(value, ovs.db.idl.Row):
            data_json[key] = str(value.uuid)

        elif value is None:
            data_json[key] = get_empty_by_basic_type(value_type)

        elif (type_ in ovs_types.IntegerType.python_types or
                type_ in ovs_types.RealType.python_types):
            data_json[key] = value

        else:
            data_json[key] = str(value)

    return data_json


def list_to_json(data, value_type=None):
    if not data:
        return data

    data_json = []
    for value in data:
        type_ = type(value)

        if isinstance(value, ovs.db.idl.Row):
            data_json.append(str(value.uuid))

        elif (type_ in ovs_types.IntegerType.python_types or
                type_ in ovs_types.RealType.python_types):
            data_json.append(value)

        elif value is None:
            data_json.append(get_empty_by_basic_type(value_type))

        else:
            data_json.append(str(value))

    return data_json


def index_to_row(index_values, table_schema, dbtable):
    """
    This subroutine fetches the row reference using index_values.
    index_values is a list which contains the combination indices
    that are used to identify a resource.
    """
    indexes = table_schema.indexes
    if len(index_values) != len(indexes):
        return None

    for row in dbtable.rows.itervalues():
        i = 0
        for index, value in zip(indexes, index_values):
            if index == 'uuid':
                if str(row.uuid) != value:
                    break
            elif str(row.__getattr__(index)) != value:
                break

            # matched index
            i += 1

        if i == len(indexes):
            return row

    return None


def kv_index_to_row(index_values, parent, idl):
    """
    This subroutine fetches the row reference using the index as key.
    Current feature uses a single index and not a combination of multiple
    indices. This is used for the new key/uuid type forward references
    introduced for BGP
    """
    index = index_values[0]
    column = parent.column
    row = idl.tables[parent.table].rows[parent.row]

    column_item = row.__getattr__(parent.column)
    for key, value in column_item.iteritems():
        if str(key) == index:
            return value

    return None


def create_index(schema, data, resource, row):
    index = None
    table = resource.next.table
    restschema = schema.ovs_tables[table]

    indexes = restschema.indexes
    if len(indexes) == 1 and indexes[0] == "uuid":
        if resource.relation == OVSDB_SCHEMA_CHILD:
            ref = schema.ovs_tables[resource.table].references[resource.column]
            if ref.kv_type:
                keyname = ref.keyname
                index = data[str(keyname)]
            else:
                index = row.uuid
    elif len(indexes) == 1:
        index = data[indexes[0]]
    else:
        tmp = []
        for item in indexes:
            tmp.append(urllib.quote(str(data[item]), safe=''))
        index = "/".join(tmp)
    return str(index)


def row_to_index(row, table, restschema, idl, parent_row=None):

    index = None
    schema = restschema.ovs_tables[table]
    indexes = schema.indexes

    # if index is just UUID
    if len(indexes) == 1 and indexes[0] == 'uuid':

        if schema.parent is not None:
            parent = schema.parent
            parent_schema = restschema.ovs_tables[parent]

            # check in parent if a child 'column' exists
            column_name = schema.plural_name
            if column_name in parent_schema.references:
                # look in all resources
                parent_rows = None
                if parent_row is not None:
                    # TODO: check if this row exists in parent table
                    parent_rows = [parent_row]
                else:
                    parent_rows = idl.tables[parent].rows.values()

                for item in parent_rows:
                    column_data = item.__getattr__(column_name)

                    if isinstance(column_data, types.ListType):
                        count = 0
                        for ref in column_data:
                            if ref == row:
                                index = str(count)
                                break
                            count+=1
                    elif isinstance(column_data, types.DictType):
                        for key, value in column_data.iteritems():
                            if value == row:
                                # found the index
                                index = key
                                break

                    if index is not None:
                        break
        else:
            index = str(row.uuid)
    else:
        tmp = []
        for item in indexes:
            tmp.append(urllib.quote(str(row.__getattr__(item)), safe=''))
        index = '/'.join(tmp)

    return index


def escaped_split(s_in):
    s_in = s_in.split('/')
    s_in = [urllib.unquote(i) for i in s_in if i != '']
    return s_in


def get_reference_uri(table_name, row, schema, idl):
    uri = OVSDB_BASE_URI
    ref_table = schema.ovs_tables[table_name]
    is_forward_ref = True

    if ref_table.parent is not None:
        _, relation = get_parent_child_col_and_relation(schema,
                                                        ref_table.parent,
                                                        table_name)

        if relation == OVSDB_SCHEMA_BACK_REFERENCE:
            is_forward_ref = False

        uri += get_reference_parent_uri(table_name, row, schema, idl)

    uri += ref_table.plural_name + '/'
    uri += '/'.join(get_table_key(row, table_name, schema, idl,
                                  is_forward_ref))

    return uri


def get_reference_parent_uri(table_name, row, schema, idl):
    uri = ''
    path = get_parent_trace(table_name, row, schema, idl)

    for table_name, indexes in path:
        if table_name == OVSDB_SCHEMA_SYSTEM_TABLE:
            continue

        plural_name = schema.ovs_tables[table_name].plural_name
        uri += str(plural_name) + '/' + "/".join(indexes) + '/'

    app_log.debug("Reference uri %s" % uri)
    return uri


def get_parent_trace(table_name, row, schema, idl):
    """
    Get the parent trace to one row
    Returns (table, index) list
    """
    table = schema.ovs_tables[table_name]
    path = []
    while table.parent is not None and row is not None:
        parent_table = schema.ovs_tables[table.parent]
        column, relation = get_parent_child_col_and_relation(schema,
                                                             table.parent,
                                                             table.name)
        if relation == OVSDB_SCHEMA_BACK_REFERENCE:
            row = get_column_data_from_row(row, column)
        else:
            row, unused_value = get_parent_row(parent_table.name, row, column,
                                               schema, idl)

        key_list = get_table_key(row, parent_table.name, schema, idl, None)
        table_path = (parent_table.name, key_list)
        path.insert(0, table_path)
        table = parent_table
    return path


def get_parent_column_ref(table_name, table_ref, schema, relation="child"):
    """
    Get column name where the child table is being referenced
    Returns column name
    """
    table = schema.ovs_tables[table_name]
    for column_name, reference in table.references.iteritems():
        if reference.ref_table == table_ref and reference.relation == relation:
            return column_name


def get_parent_row(table_name, child_row, column, schema, idl):
    """
    Get the row where the item is being referenced
    Returns idl.Row object
    """
    table = schema.ovs_tables[table_name]
    for uuid, row_ref in idl.tables[table_name].rows.iteritems():
        reflist = get_column_data_from_row(row_ref, column)
        for value in reflist:
            if table.references[column].kv_type:
                db_col = row_ref.__getattr__(column)
                row_value = db_col[value]
                if row_value.uuid == child_row.uuid:
                    return row_ref, value
            else:
                if value.uuid == child_row.uuid:
                    return row_ref, None


def get_table_key(row, table_name, schema, idl, forward_ref=True):
    """
    Get the row index
    Return the row index
    """
    key_list = []
    table = schema.ovs_tables[table_name]

    # Verify if is kv reference
    if table.parent:
        column_ref = None

        if forward_ref is None:
            forward_ref = True
            column_ref, relation = \
                get_parent_child_col_and_relation(schema, table.parent,
                                                  table_name)

            if relation == OVSDB_SCHEMA_BACK_REFERENCE:
                forward_ref = False

        if forward_ref:
            cur_table_name = table.parent
            table_ref = table_name
            relation = OVSDB_SCHEMA_CHILD
        else:
            cur_table_name = table_name
            table_ref = table.parent
            relation = OVSDB_SCHEMA_PARENT

        if column_ref is None:
            column_ref = get_parent_column_ref(cur_table_name, table_ref,
                                               schema, relation)

        cur_table = schema.ovs_tables[cur_table_name]
        if cur_table.references[column_ref].kv_type:
            parent_row, key = get_parent_row(cur_table_name,
                                             row, column_ref, schema, idl)
            key_list.append(str(key))
            return key_list

    # If not is a kv_reference return the index
    indexes = table.indexes
    for index in indexes:
        if index == 'uuid':
            key_list.append(str(row.uuid))
        else:
            value = urllib.quote(str(row.__getattr__(index)), safe='')
            key_list.append(value)

    return key_list


def exec_validators_with_resource(idl, schema, resource, http_method):
    p_table_name = None
    p_row = None
    child_resource = resource

    # Set parent info if a child exists
    if resource.next is not None:
        p_table_name = resource.table
        p_row = idl.tables[p_table_name].rows[resource.row]
        child_resource = resource.next

    table_name = child_resource.table
    if child_resource.row is None and resource.relation == OVSDB_SCHEMA_CHILD:
        children = p_row.__getattr__(resource.column)
        if isinstance(children, ovs.db.idl.Row):
            children = [children]
        elif isinstance(children, dict):
            children = children.values()
        for row in children:
            validator.exec_validators(idl, schema, table_name, row, http_method,
                                      p_table_name, p_row)

    elif child_resource.row is None and resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
        p_row = idl.tables[p_table_name].rows[resource.row]
        refcol = None
        refkeys = schema.ovs_tables[table_name].references
        for key, value in refkeys.iteritems():
            if (value.relation == OVSDB_SCHEMA_PARENT and
                    value.ref_table == p_table_name):
                refcol = key
                break

        for row in idl.tables[child_resource.table].rows.itervalues():
            if row.__getattr__(refcol) == p_row:
                validator.exec_validators(idl, schema, table_name, row,
                                          http_method, p_table_name, p_row)
    else:
        row = idl.tables[table_name].rows[child_resource.row]
        validator.exec_validators(idl, schema, table_name, row, http_method,
                                  p_table_name, p_row)


def redirect_http_to_https(current_instance):
    if not options.force_https:
        return True

    if current_instance.request.protocol == HTTP:
        current_instance.redirect(re.sub(r'^([^:]+)', HTTPS,
                                  current_instance.request.full_url()), True)
        return True

    return False


def update_category_keys(keys, row, idl, schema, table):
    """
    Update the keys categories for a given resource
    Parameters:
        -keys: dictionary of key columns
        (configuration,status,statistics, references)
        -row: ovs.db.idl.Row or dict object if it's new data
        -schema: RestSchema
        -idl: Idl instance
        -table: table name
    """
    if row is None \
            or not isinstance(row, (ovs.db.idl.Row, dict)):
        app_log.debug("No row or data to process")
        return keys

    # Process dynamic columns
    if isinstance(row, ovs.db.idl.Row)\
            and idl is None or schema is None:
        app_log.debug("Resource, Idl or schema is None")
        return keys

    ovs_table = schema.ovs_tables[table]
    if not ovs_table.dynamic:
        app_log.debug("Nothing to do the table doesn't "
                      "have dynamic columns")
        return keys

    # Get all columns
    columns = {}
    columns.update(keys[OVSDB_SCHEMA_CONFIG])
    columns.update(keys[OVSDB_SCHEMA_STATUS])
    columns.update(keys[OVSDB_SCHEMA_STATS])
    references = keys[OVSDB_SCHEMA_REFERENCE]

    dynamic_columns = ovs_table.dynamic
    for column_name, category_obj in dynamic_columns.iteritems():
        # Store the column used to get the category value
        if category_obj.follows is not None:
            source_column = category_obj.follows
        elif category_obj.per_value is not None:
            source_column = column_name

        column_data = None
        # Get column data from follows/per_value
        if isinstance(row, ovs.db.idl.Row):
            column_data = get_column_data_from_row(row, source_column)
        elif isinstance(row, dict):
            if source_column in row:
                column_data = row[source_column]
            else:
                app_log.debug("per-value column '%s' is not present"
                              % source_column)
                raise Exception("Attribute '%s' is required "
                                "by attribute '%s'."
                                % (source_column, column_name))

        # Set the new category
        # Get new category for that value using per-value data
        new_category = \
            columns[source_column].category.per_value[column_data]

        # Store old category
        if column_name in references:
            prev_category = references[column_name].category.value
        else:
            prev_category = columns[column_name].category.value

        # Check if the category changed
        if prev_category != new_category:
            if column_name in columns:
                orig_columns = keys[prev_category]
                dest_columns = keys[new_category]
                # Change the category
                column = orig_columns[column_name]
                column.category.value = new_category
                dest_columns[column_name] = column
                orig_columns.pop(column_name)

            # If the column is at references change the category
            if column_name in references:
                reference = references[column_name]
                reference.category.value = new_category

    return keys


def update_resource_keys(resource, schema, idl, data=None):
    """
    Update the keys categories for a given resource

    Parameters:
        resource: opsrest.Resource instance
        schema: RestSchema
        idl: Idl instance
        data: json data given if the resource is new and doesn't
             have a row.
    """
    row = None
    if data is not None:
        row = data
    elif resource.row:
        row = get_row_from_resource(resource, idl)

    try:
        resource.keys = update_category_keys(resource.keys, row, idl,
                                             schema, resource.table)
    except Exception as e:
        raise DataValidationFailed(str(e))


def get_parent_child_col_and_relation(schema, parent_table, child_table):
    parent_schema = schema.ovs_tables[parent_table]
    for column, reference in parent_schema.references.iteritems():
        if child_table == reference.ref_table:
            if (reference.relation == OVSDB_SCHEMA_CHILD or
                    reference.relation == OVSDB_SCHEMA_REFERENCE):
                return (column, reference.relation)

    child_schema = schema.ovs_tables[child_table]
    for column, reference in child_schema.references.iteritems():
        if parent_table == reference.ref_table:
            if reference.relation == OVSDB_SCHEMA_PARENT:
                return (column, OVSDB_SCHEMA_BACK_REFERENCE)

    return (None, None)

def row_to_uri(row, table, schema, idl):

    path = []
    while row:
        # top level table
        if not schema.ovs_tables[table].parent:
            index = str(row_to_index(row, table, schema, idl))
            path = [index, schema.ovs_tables[table].plural_name]
            table = OVSDB_SCHEMA_SYSTEM_TABLE
        else:
            parent_table = schema.ovs_tables[table].parent
            parent_row = None
            if table in schema.ovs_tables[parent_table].children:
                # backward
                for x, y in schema.ovs_tables[table].references.iteritems():
                    if y.relation == OVSDB_SCHEMA_PARENT:
                        parent_row = row.__getattr__(x)
                        break
                index = str(row_to_index(row, table, schema, idl, parent_row))
                path = path + [index, schema.ovs_tables[table].plural_name]
            else:
                # forward
                for name, column in schema.ovs_tables[parent_table].references.iteritems():
                    if column.relation == OVSDB_SCHEMA_CHILD and column.ref_table == table:
                        break

                for item in idl.tables[parent_table].rows.itervalues():
                    children = item.__getattr__(name)
                    if isinstance(children, ovs.db.idl.Row):
                        children = [children]
                    elif isinstance(children, dict):
                        children = children.values()

                    if row in children:
                        parent_row = item
                        break

                _max = column.n_max
                if _max == 1:
                    path = path + [name]
                else:
                    index = str(row_to_index(row, table, schema, idl, parent_row))
                    path = path + [index, name]

            row = parent_row
            table = parent_table

        if table == OVSDB_SCHEMA_SYSTEM_TABLE:
            path = path + [OVSDB_SCHEMA_SYSTEM_URI]
            break

    path.reverse()
    uri = REST_VERSION_PATH + '/'.join(path)
    return uri

def get_back_reference_children(parent, parent_table, child_table, schema, idl):
    references = schema.ovs_tables[child_table].references
    refcol = None
    for key, value in references.iteritems():
        if (value.relation == OVSDB_SCHEMA_PARENT and
                value.ref_table == parent_table):
            refcol = key
            break
    if refcol is None:
        return None

    children = []
    for row in idl.tables[child_table].rows.itervalues():
        if row.__getattr__(refcol) == parent:
            children.append(row)
    return children

@gen.coroutine
def fetch_readonly_columns(schema, table, idl, manager, rows):
    """
    Fetches the columns that were registered as read-only from the DB.
    The method utilizes commit_block. Top-level caller should invoke this
    in a coroutine.
    """
    if table in ON_DEMAND_FETCHED_TABLES:
        app_log.debug("Fetching read-only columns..")
        table_schema = schema.ovs_tables[table]
        txn = manager.get_new_transaction()

        for row in rows:
            for column in table_schema.readonly_columns:
                row.fetch(column)

        status = txn.commit()
        if status == INCOMPLETE:
            manager.monitor_transaction(txn)
            yield txn.event.wait()
            status = txn.status

        app_log.debug("Fetching status: %s" % status)


@gen.coroutine
def fetch_readonly_columns_for_table(schema, table, idl, manager):
    """
    Fetches the columns that were registered as read-only from the DB
    for all rows in the table.

    The method utilizes commit_block. Top-level caller should invoke this
    in a coroutine.
    """
    if table in ON_DEMAND_FETCHED_TABLES:
        app_log.debug("Fetching read-only columns for table..")
        table_schema = schema.ovs_tables[table]
        txn = manager.get_new_transaction()

        for column in table_schema.readonly_columns:
            txn.txn.fetch_table(table, column)

        status = txn.commit()
        if status == INCOMPLETE:
            manager.monitor_transaction(txn)
            yield txn.event.wait()
            status = txn.status

        app_log.debug("Fetching status: %s" % status)
