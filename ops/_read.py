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

import ops.constants
import ops.utils
import ovs.db.idl

import ovs.vlog
vlog = ovs.vlog.Vlog('dc')


def get_row_data(row, table_name, schema, idl, index=None):

    if index is None:
        index = ops.utils.row_to_index(row, table_name, schema, idl)

    row_data = {}

    # NOTE: remove this when we have a proper
    # solution for TG-1116
    if table_name == 'VLAN':
        internal_usage = row.__getattr__('internal_usage')
        if internal_usage:
            return None

    # Iterate over all columns in the row
    table_schema = schema.ovs_tables[table_name]

    # get dyanmic categories
    categories = ops.utils.get_dynamic_categories(row, table_name, schema, idl)

    # are of type 'status', we skip the row
    if not ops.utils.has_config_category(categories):
        return None

    # Iterate over all children (forward and backward references) in the row
    for child_name in table_schema.children:

        # Forward reference
        # Two types of forward references exist
        # - regular (List of uuid)
        # - key/value type (Dict type)

        children_data = {}
        indexer = 0
        if child_name in table_schema.references:
            column_data = row.__getattr__(child_name)
            child_table_name = table_schema.references[child_name].ref_table

            # Check kv_type references
            keys = None
            kv_type = table_schema.references[child_name].kv_type
            if kv_type and isinstance(column_data, dict):
                keys = column_data.keys()
                column_data = column_data.values()

            # Iterate through all items in column_data
            count = 0
            for item in column_data:
                if kv_type:
                    kv_index = keys[count]
                    data = get_row_data(
                        item, child_table_name, schema,
                        idl, kv_index)
                    if data is None:
                        continue

                    children_data.update({str(keys[count]): data.values()[0]})
                    count = count + 1
                else:
                    data = get_row_data(item, child_table_name, schema, idl)
                    if data is None:
                        continue

                    _indexes = schema.ovs_tables[child_table_name].indexes
                    if len(_indexes) == 1 and _indexes[0] == 'uuid':
                        indexer = indexer + 1
                        child_index = child_table_name + str(indexer)
                        data = {child_index: data.values()[0]}
                    children_data.update(data)

        # Backward reference
        else:
            column_name = None
            # Find the 'parent' name from child table (back referenced child)
            # e.g. in Route table 'vrf' column is the 'parent' column
            for name, column in (schema.ovs_tables[child_name].
                                 references.iteritems()):
                if column.relation == ops.constants.OVSDB_SCHEMA_PARENT:
                    # Found the parent column
                    column_name = name
                    break

            # Iterate through entire child table to find those rows belonging
            # to the same parent
            for item in idl.tables[child_name].rows.itervalues():
                # Get the parent row reference
                ref = item.__getattr__(column_name)
                # Parent reference is same as 'row' (row was passed to
                #this function) this is now the child of 'row'
                if ref.uuid == row.uuid:
                    data = get_row_data(item, child_name, schema, idl)
                    if data is not None:
                        children_data.update(data)

        if children_data:
            row_data[child_name] = children_data

    # Iterate through 'references' from table
    for refname, refobj in categories[ops.constants.OVSDB_SCHEMA_REFERENCE].iteritems():
        _min = refobj.n_min
        _max = refobj.n_max
        ref_table_name = table_schema.references[refname].ref_table

        if refobj.relation == ops.constants.OVSDB_SCHEMA_REFERENCE\
                and refobj.category == ops.constants.OVSDB_SCHEMA_CONFIG:
            references = row.__getattr__(refname)
            if not references:
                continue

            refdata = None
            if isinstance(references, ovs.db.idl.Row):
                if not (_min == 1 and _max == 1):
                    raise Exception("datatype for column %s in " % refname +
                                    "table %s must be a UUID" % table_name)
                else:
                    refdata = ops.utils.row_to_index(references,
                                                     ref_table_name,
                                                     schema, idl)
            elif isinstance(references, dict):
                refdata = {}
                for key, ref in references.iteritems():
                    ref_index = ops.utils.row_to_index(ref,
                                                       ref_table_name,
                                                       schema, idl)
                    refdata.update({str(key): str(ref_index)})
            elif isinstance(references, list):
                if _max == 1:
                    if len(references)>1:
                        raise Exception("max 1 entry allowed for column %s " %refname +
                                        " in table %" % table_name)

                    refdata = ops.utils.row_to_index(references[0],
                                                     ref_table_name,
                                                     schema, idl)
                else:
                    refdata = []
                    for ref in references:
                        ref_index = ops.utils.row_to_index(ref,
                                                           ref_table_name,
                                                           schema, idl)
                        refdata.append(ref_index)
            else:
                raise Exception("datatype for column %s in " % refname +
                                "table %s is not supported" % table_name)

            row_data[refname] = refdata

    for column_name in categories[ops.constants.OVSDB_SCHEMA_CONFIG]:
        column_data = row.__getattr__(column_name)

        # Do not include empty columns
        if column_data is None or column_data == {} or column_data == [] or column_data == '':
            continue

        row_data[column_name] = column_data

    if row_data:
        # get all non-config index columns
        for key in table_schema.indexes:

            if key is 'uuid':
                continue

            if key not in categories[ops.constants.OVSDB_SCHEMA_CONFIG] and key not in row_data:
                row_data[key] = row.__getattr__(key)

        vlog.dbg('read row %s with index %s from table %s' % (str(row.uuid), index, table_name))
        return {index: row_data}

    return None


def get_table_data(table_name, schema, idl):

    # get the table from the DB
    table = idl.tables[table_name]

    # Iterate over all rows
    table_data = {table_name: {}}

    # If table is empty return None
    if len(table.rows) == 0:
        vlog.dbg('table %s is empty' % table_name)
        return None

    for row in table.rows.itervalues():
        row_data = get_row_data(row, table_name, schema, idl)
        if row_data is None:
            continue
        table_data[table_name].update(row_data)

    if not table_data.values()[0]:
        return None
    else:
        return table_data
