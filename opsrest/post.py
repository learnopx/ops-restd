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

from opsrest.constants import *
from opsrest.utils import utils
from opsrest import verify
from opsrest.transaction import OvsdbTransactionResult
from opsrest.exceptions import MethodNotAllowed, DataValidationFailed
from opsvalidator.error import ValidationError

from tornado.log import app_log


def post_resource(data, resource, schema, txn, idl):
    """
    /system/bridges: POST allowed as we are adding a new Bridge
                     to a child table
    /system/ports: POST allowed as we are adding a new Port to
                   top level table
    /system/vrfs/vrf_default/bgp_routers: POST allowed as we
                   are adding a back referenced resource
    /system/bridges/bridge_normal/ports: POST NOT allowed as we
    are attemtping to add a Port as a reference on bridge
    """

    if resource is None or resource.next is None:
        app_log.info("POST is not allowed on System table")
        raise MethodNotAllowed

    # get the last resource pair
    while True:
        if resource.next.next is None:
            break
        resource = resource.next

    utils.update_resource_keys(resource.next, schema,
                               idl, data[OVSDB_SCHEMA_CONFIG])

    if verify.verify_http_method(resource, schema,
                                 REQUEST_TYPE_CREATE) is False:
        raise MethodNotAllowed

    # verify data
    try:
        verified_data = verify.verify_data(data, resource, schema, idl,
                                           REQUEST_TYPE_CREATE)
    except DataValidationFailed as e:
        app_log.debug(e)
        raise e

    app_log.debug("adding new resource to " + resource.next.table + " table")

    if resource.relation == OVSDB_SCHEMA_CHILD:
        # create new row, populate it with data
        # add it as a reference to the parent resource
        new_row = utils.setup_new_row_by_resource(resource.next, verified_data,
                                                  schema, txn, idl)

        ref = schema.ovs_tables[resource.table].references[resource.column]
        if ref.kv_type:
            keyname = ref.keyname
            utils.add_kv_reference(verified_data[keyname],
                                   new_row, resource, idl)
        else:
            utils.add_reference(new_row, resource, idl)

    elif resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
        # row for a back referenced item contains the parent's reference
        # in the verified data
        new_row = utils.setup_new_row_by_resource(resource.next, verified_data,
                                                  schema, txn, idl)

    elif resource.relation == OVSDB_SCHEMA_TOP_LEVEL:
        new_row = utils.setup_new_row_by_resource(resource.next, verified_data,
                                                  schema, txn, idl)

        # a non-root table entry MUST be referenced elsewhere
        if OVSDB_SCHEMA_REFERENCED_BY in verified_data:
            for reference in verified_data[OVSDB_SCHEMA_REFERENCED_BY]:
                utils.add_reference(new_row, reference, idl)

    try:
        utils.exec_validators_with_resource(idl, schema, resource,
                                            REQUEST_TYPE_CREATE)
    except ValidationError as e:
        app_log.debug("Custom validations failed:")
        app_log.debug(e.error)
        raise DataValidationFailed(e.error)

    index = utils.create_index(schema, verified_data, resource, new_row)
    result = txn.commit()

    return OvsdbTransactionResult(result, index)
