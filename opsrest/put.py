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


def put_resource(data, resource, schema, txn, idl):

    # Allow PUT operation on System table
    if resource is None:
        raise MethodNotAllowed

    # We want to modify System table
    if resource.next is None:
        resource_update = resource
    else:
        while True:
            if resource.next.next is None:
                break
            resource = resource.next
        resource_update = resource.next

    app_log.debug("Resource = Table: %s Relation: %s Column: %s"
                  % (resource.table, resource.relation, resource.column))

    utils.update_resource_keys(resource_update, schema, idl)

    if resource_update is None or resource_update.row is None or\
            verify.verify_http_method(resource,
                                      schema, REQUEST_TYPE_UPDATE) is False:
        raise MethodNotAllowed

    # verify data
    try:
        verified_data = verify.verify_data(data, resource, schema, idl,
                                           REQUEST_TYPE_UPDATE)
    except DataValidationFailed as e:
        app_log.debug(e)
        raise e

    # We want to modify System table
    if resource.next is None:
        updated_row = utils.update_row(resource_update, verified_data,
                                       schema, txn, idl)

    elif resource.relation == OVSDB_SCHEMA_CHILD:
        '''
        Updating row from a child table
        Example:
        /system/bridges: PUT is allowed when modifying the bridge child table
        '''
        # update row, populate it with data, add it as a reference to
        # the parent resource
        updated_row = utils.update_row(resource_update,
                                       verified_data, schema, txn, idl)

    elif resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
        '''
        In this case we only modify the data of the table, but we not modify
        the back reference.
        Example:
        /system/vrfs/vrf_default/bgp_routers: PUT allowed as we are
         modifying a back referenced resource
        '''
        # row for a back referenced item contains the parent's reference
        # in the verified data
        updated_row = utils.update_row(resource_update, verified_data,
                                       schema, txn, idl)

    elif resource.relation == OVSDB_SCHEMA_TOP_LEVEL:
        '''
        Updating row when we have a relationship with a top_level table
        Is not allowed to update the references in other tables.
        Example:
        /system/ports: PUT allowed as we are modifying Port to top level table
        '''
        updated_row = utils.update_row(resource_update, verified_data,
                                       schema, txn, idl)

    try:
        utils.exec_validators_with_resource(idl, schema, resource,
                                            REQUEST_TYPE_UPDATE)
    except ValidationError as e:
        app_log.debug("Custom validations failed:")
        app_log.debug(e.error)
        raise DataValidationFailed(e.error)

    result = txn.commit()
    return OvsdbTransactionResult(result)
