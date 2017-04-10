# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
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

from opsrest.constants import *
from opsrest.utils import utils
from opsrest import verify
from opsrest.transaction import OvsdbTransactionResult
from opsrest.exceptions import MethodNotAllowed, DataValidationFailed
from opsvalidator import validator
from opsvalidator.error import ValidationError

import ovs.db.idl
import httplib
from tornado.log import app_log


def delete_resource(resource, schema, txn, idl):

    if resource.next is None:
        return None

    # get the last resource pair
    while True:
        if resource.next.next is None:
            break
        resource = resource.next

    # Check for invalid resource deletion
    if verify.verify_http_method(resource, schema,
                                 REQUEST_TYPE_DELETE) is False:
        raise MethodNotAllowed

    try:
        utils.exec_validators_with_resource(idl, schema, resource,
                                            REQUEST_TYPE_DELETE)
    except ValidationError as e:
        app_log.debug("Custom validations failed:")
        app_log.debug(e.error)
        raise DataValidationFailed(e.error)

    if resource.relation == OVSDB_SCHEMA_CHILD:
        if resource.next.row is None:
            parent = idl.tables[resource.table].rows[resource.row]
            rows = parent.__getattr__(resource.column)
            if isinstance(rows, dict):
                rows = rows.values()
                parent.__setattr__(resource.column, {})
            elif isinstance(rows, ovs.db.idl.Row):
                rows = [rows]
                parent.__setattr__(resource.column, None)
            else:
                parent.__setattr__(resource.column, [])

            # delete rows from the table
            while len(rows):
                row = rows.pop()
                row.delete()
        else:
            row = utils.delete_reference(resource.next, resource, schema, idl)
            row.delete()

    elif resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
        if resource.next.row is None:
            refcol = None
            parent = idl.tables[resource.table].rows[resource.row]
            refkeys = schema.ovs_tables[resource.next.table].references
            for key, value in refkeys.iteritems():
                if (value.relation == OVSDB_SCHEMA_PARENT and
                        value.ref_table == resource.table):
                    refcol = key
                    break

            children = []
            for row in idl.tables[resource.next.table].rows.itervalues():
                if row.__getattr__(refcol) == parent:
                    children.append(row.uuid)

            for child in children:
                row = idl.tables[resource.next.table].rows[child]
                row.delete()
        else:
            row = utils.get_row_from_resource(resource.next, idl)
            row.delete()
    elif resource.relation == OVSDB_SCHEMA_TOP_LEVEL:
        row = utils.delete_all_references(resource.next, schema, idl)

        # Check if the table is a top-level root table that is not referenced
        # and explicitly delete.
        resource_table = resource.next.table
        if resource_table not in schema.reference_map.values():
            if schema.ovs_tables[resource_table].is_root:
                row.delete()

    result = txn.commit()
    return OvsdbTransactionResult(result)
