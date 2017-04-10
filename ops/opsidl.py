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


from ovs.db.idl import Idl, Row
import ovs


class OpsIdl(Idl):
    """
    OpsIdl inherits from Class Idl. The index to row mapping feature
    is used in order to improve dc write time by doing the lookup from
    the index_map.

    """
    def __init__(self, remote, schema):
        Idl.__init__(self, remote, schema)
        self._clear_all_index_maps()

    def _Idl__clear(self):
        self._clear_all_index_maps()
        Idl._Idl__clear(self)

    def _clear_all_index_maps(self):
        for table in self.tables.itervalues():
            table.index_map = {}

    # Overriding parent process_update
    def _Idl__process_update(self, table, uuid, old, new):
        """Returns True if a column changed, False otherwise."""
        row = table.rows.get(uuid)
        changed = Idl._Idl__process_update(self, table, uuid, old, new)

        if not new:
            if row:
                # Delete row.
                self._update_index_map(row, table, ovs.db.idl.ROW_DELETE)
        elif not old or not row:
            # Create row.
            row = table.rows.get(uuid)
            self._update_index_map(row, table, ovs.db.idl.ROW_CREATE, new)

        return changed

    def _update_index_map(self, row, table, operation, new=None):

        if operation == ovs.db.idl.ROW_DELETE:
            index = self._row_to_index_lookup(row, table)
            if index in table.index_map:
                del table.index_map[index]

        elif operation == ovs.db.idl.ROW_CREATE:
            if table.indexes:
                index_values = []
                for v in table.indexes[0]:
                    if v.name in row._data:
                        column = table.columns.get(v.name)
                        if column.type.key.type == ovs.db.types.UuidType:
                            val = new[v.name][1]
                        else:
                            val = row.__getattr__(v.name)
                        val = str(val)
                        index_values.append(val)
                table.index_map[tuple(index_values)] = row

    def index_to_row_lookup(self, index, table_name):
        """
        This subroutine fetches the row reference using index_values.
        index_values is a list which contains the combination indices
        that are used to identify a resource.
        """
        table = self.tables.get(table_name)
        index = tuple([str(item) for item in index])
        if index in table.index_map:
            return table.index_map[index]

        return None

    def _row_to_index_lookup(self, row, table):
        # Given the row return the index
        index_values = []
        if not table.indexes:
            return None
        for v in table.indexes[0]:
            val = row.__getattr__(v.name)
            if isinstance(val, Row):
                val = val.uuid
            val = str(val)
            index_values.append(val)
        return tuple(index_values)
