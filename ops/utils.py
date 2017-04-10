#  Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import ovs
import urllib
import types
import uuid
import six

import ovs.db.types as ovs_types
import ops.constants
import opsrest.utils.utils

def unquote_split(s_in):
    if isinstance(s_in, six.string_types):
        s_in = s_in.split('/')
        s_in = [urllib.unquote(i) for i in s_in if i != '']
        return s_in
    else:
        return [str(s_in)]


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
    else:
        return None


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
                    parent_rows = idl.tables[parent].rows

                for item in parent_rows.itervalues():
                    column_data = item.__getattr__(column_name)

                    if isinstance(column_data, types.ListType):
                        for ref in column_data:
                            if ref.uuid == row:
                                index = str(row.uuid)
                                break
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
            value = row.__getattr__(item)
            if isinstance(value, ovs.db.idl.Row):
                refTable = schema.references[item].ref_table
                value = row_to_index(value, refTable, restschema, idl)
            tmp.append(urllib.quote(str(value), safe=''))
        index = '/'.join(tmp)

    return index


def index_to_row(index, extschema, table, idl):
    """
    This subroutine fetches the row reference using index.
    index is either of type uuid.UUID or is a uri escaped string which contains
    the combination indices that are used to identify a resource.
    """
    table_schema = extschema.ovs_tables[table]
    if isinstance(index, uuid.UUID):
        # index is of type UUID
        if index in idl.tables[table].rows:
            return idl.tables[table].rows[index]
        else:
            raise Exception("""resource with UUID %(i) not found
                            in table %(j)
                            """ % {"i":str(index), "j":table})
    else:
        # index is an escaped combine indices string
        index_values = unquote_split(index)
        indexes = table_schema.index_columns

        # if table has no indexes, we create a new entry
        if not table_schema.index_columns:
            return None

        if len(index_values) != len(indexes):
            raise Exception('Combination index error for table %s' % table)
        updated_index_val = []
        # Converting reference index to row pointers
        for key, value in zip(indexes, index_values):
            if key in table_schema.references.keys():
                refTable = table_schema.references[key].ref_table
                refRow = index_to_row(value, extschema, refTable, idl)
                if refRow is None:
                    continue
                updated_index_val.append(refRow.uuid)
            else:
                updated_index_val.append(value)

        # find in IDL index_map
        return idl.index_to_row_lookup(updated_index_val, table)


def delete_row_check(row, table, extschema, idl):
    table_schema = extschema.ovs_tables[table]
    categories = get_dynamic_categories(row, table, extschema, idl)
    return check_row_mutable(table, categories, extschema)


def insert_row_check(data, table, extschema, idl, txn):
    table_schema = extschema.ovs_tables[table]
    row = txn.insert(idl.tables[table])
    set_default_config_columns(data, row, table, extschema, True)
    categories = get_dynamic_categories(row, table, extschema, idl)

    if check_row_mutable(table, categories, extschema, True):
        return row
    else:
        row.delete()
        return None


def check_row_mutable(table, categories, extschema, insert=False):
    table_schema = extschema.ovs_tables[table]
    if table_schema.dynamic:
        if has_config_category(categories):
            if has_config_index(table, extschema, categories):
                return True
            elif table_schema.indexes == ['uuid'] and not is_immutable_table(table, extschema):
                return True
            elif table_schema.indexes == ['uuid'] and insert:
                return True
    else:
        if not is_immutable_table(table, extschema):
            return True
        elif table_schema.indexes == ['uuid'] and insert:
            return True

    return False


def set_config_columns(data, row, table, extschema, idl):
    categories = get_dynamic_categories(row, table, extschema, idl)
    table_schema = extschema.ovs_tables[table]
    changed = False
    for key in categories[ops.constants.OVSDB_SCHEMA_CONFIG].keys():
        if categories[ops.constants.OVSDB_SCHEMA_CONFIG][key].mutable:
            if key in data:
                if hasattr(row, key):
                    value = row.__getattr__(key)
                    if data[key] == value:
                        continue
                row.__setattr__(key, data[key])
            else:
                value =  ops.utils.get_empty_by_basic_type(row.__getattr__(key))
                if row.__getattr__(key) == value:
                    continue
                row.__setattr__(key, value)
            # flag to track if row was modified
            changed = True

    return changed


def set_default_config_columns(data, row, table, extschema, new=False):
    table_schema = extschema.ovs_tables[table]
    for key in table_schema.default_config.keys():
        if not new and not table_schema.default_config[key].mutable:
            continue

        if key not in data:
            if new or row.__getattr__(key) is None:
                continue
            else:
                value =  ops.utils.get_empty_by_basic_type(row.__getattr__(key))
                row.__setattr__(key, value)
        else:
            value = data[key]
            row.__setattr__(key, value)

    if new:
        for key in table_schema.indexes:
            if key is 'uuid':
                continue

            if key not in table_schema.default_config.keys() and key in data:
                row.__setattr__(key, data[key])

    return True

def get_default_categories(table, extschema):
    table_schema = extschema.ovs_tables[table]
    categories = {ops.constants.OVSDB_SCHEMA_CONFIG: table_schema.config,
            ops.constants.OVSDB_SCHEMA_STATUS: table_schema.status,
            ops.constants.OVSDB_SCHEMA_STATS:  table_schema.stats,
            ops.constants.OVSDB_SCHEMA_REFERENCE: table_schema.references}
    return categories


def get_dynamic_categories(row, table, extschema, idl):
    categories = get_default_categories(table, extschema)
    table_schema = extschema.ovs_tables[table]
    if table_schema.dynamic:
        return opsrest.utils.utils.update_category_keys(categories,
                                                        row, idl,
                                                        extschema,
                                                        table)
    else:
        return categories


def has_config_category(categories):
    if not categories[ops.constants.OVSDB_SCHEMA_CONFIG]:
        for k, v in categories[ops.constants.OVSDB_SCHEMA_REFERENCE].iteritems():
            if v.category == ops.constants.OVSDB_SCHEMA_CONFIG:
                return True
        return False
    return True


def has_config_index(table, extschema, categories):
    index_columns = extschema.ovs_tables[table].index_columns
    for index in index_columns:
        if index in categories[ops.constants.OVSDB_SCHEMA_CONFIG]:
            return True
        elif index in categories[ops.constants.OVSDB_SCHEMA_REFERENCE]:
            if categories[ops.constants.OVSDB_SCHEMA_REFERENCE][index].category ==\
                    ops.constants.OVSDB_SCHEMA_CONFIG:
                        return True
    return False


def config_child_column(column, table, extschema, categories):
    table_schema = extschema.ovs_tables[table]
    child_table = table_schema.references[column].ref_table
    config = True
    if table_schema.dynamic:
        if categories[ops.constants.OVSDB_SCHEMA_REFERENCE][key].category !=\
                ops.constants.OVSDB_SCHEMA_CONFIG:
                    config = False
    elif ops.utils.is_immutable_table(child_table, extschema):
        config = False

    return config

def is_immutable_table(table, extschema):
    default_tables = ['Bridge', 'VRF']
    if extschema.ovs_tables[table].mutable and table not in default_tables:
        return False
    return True
