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

from opsrest.constants import *
from opsrest.utils import utils, getutils
from opsrest import verify
from opsrest import get
from opsrest.transaction import OvsdbTransactionResult
from opsrest.exceptions import MethodNotAllowed, DataValidationFailed, \
    PatchOperationFailed
from opsvalidator.error import ValidationError

import jsonpatch

from jsonpointer import JsonPointerException
from tornado.log import app_log
from copy import deepcopy
from tornado import gen


@gen.coroutine
def patch_resource(data, resource, schema, txn, idl, uri):

    # Allow PATCH operation on System table
    if resource is None:
        raise MethodNotAllowed

    app_log.debug("Resource = Table: %s Relation: %s Column: %s" %
                  (resource.table, resource.relation, resource.column))

    # We want to modify System table
    if resource.next is None:
        resource_update = resource
    else:
        while True:
            if resource.next.next is None:
                break
            resource = resource.next
        resource_update = resource.next

    utils.update_resource_keys(resource_update, schema, idl)

    if resource_update is None or resource_update.row is None or \
            verify.verify_http_method(resource, schema,
                                      REQUEST_TYPE_PATCH) is False:
        app_log.debug("Failed http_method verification")
        raise MethodNotAllowed

    needs_update = False

    # Create and verify patch
    (patch, needs_update) = create_patch(data)

    # Get the JSON to patch
    row_json = yield get_current_row(resource_update, uri, schema, idl)

    # Now apply the patch to that JSON
    patched_row_json = apply_patch(patch, row_json, resource_update, schema)

    # If at least one PATCH operation changed the row,
    # since a valid patch can contain just a PATCH_OP_TEST,
    # validate the patched row and update row with IDL
    if needs_update:

        # Validate and prepare final JSON to send to IDL
        new_row_json = prepare_data(patch, patched_row_json, resource,
                                    resource_update, schema, idl)

        app_log.debug("New row -> %s" % new_row_json)

        # Update resource with the patched JSON
        # System: resource.next is None
        # All other rows: resource.relation is not None
        if resource.next is None or resource.relation is not None:
            app_log.debug("Updating row...")
            # updated_row is not used for now but eventually will be returned
            updated_row = utils.update_row(resource_update, new_row_json,
                                           schema, txn, idl)

        try:
            utils.exec_validators_with_resource(idl, schema, resource,
                                                REQUEST_TYPE_PATCH)
        except ValidationError as e:
            app_log.debug("Custom validations failed:")
            app_log.debug(e.error)
            raise DataValidationFailed(e.error)

    result = txn.commit()
    raise gen.Return(OvsdbTransactionResult(result))


def create_patch(data):

    try:
        patch = jsonpatch.JsonPatch(data)
    except:
        raise DataValidationFailed("Malformed JSON patch")

    app_log.debug("PATCH Created patch object %s" % patch.to_string())

    if not patch:
        raise DataValidationFailed("Empty JSON patch")

    # Sanity check for patch operations
    # NOTE supposedly jsonpatch verifies this and the resulting patch should
    # evaluate to True if it contains at least one operation, but this doesn't
    # seem to be the case in practice as any valid JSON is accepted, therefore
    # the next sanity check verifies the patch's operations.

    common_keys = (PATCH_KEY_OP, PATCH_KEY_PATH)
    operation_keys = {}
    operation_keys[PATCH_OP_TEST] = (PATCH_KEY_VALUE,)
    operation_keys[PATCH_OP_REMOVE] = ()
    operation_keys[PATCH_OP_ADD] = (PATCH_KEY_VALUE,)
    operation_keys[PATCH_OP_REPLACE] = (PATCH_KEY_VALUE,)
    operation_keys[PATCH_OP_MOVE] = (PATCH_KEY_FROM,)
    operation_keys[PATCH_OP_COPY] = (PATCH_KEY_FROM,)

    patch_list = patch.patch

    modified = False
    for patch_op in patch_list:

        if PATCH_KEY_OP not in patch_op:
            raise DataValidationFailed("Missing PATCH operation key")

        current_op = patch_op[PATCH_KEY_OP]

        if current_op not in operation_keys:
            raise DataValidationFailed("PATCH operation not supported")

        # NOTE add any other non-modifying op to this condition
        if current_op != PATCH_OP_TEST:
            modified = True

        valid_keys = set([])
        valid_keys.update(common_keys)
        valid_keys.update(operation_keys[current_op])

        op_keys = set(patch_op.keys())

        unknown_keys = op_keys.difference(valid_keys)
        if unknown_keys:
            raise DataValidationFailed("Invalid keys '%s' for operation '%s'" %
                                       (list(unknown_keys), current_op))

        missing_keys = valid_keys.difference(op_keys)
        if missing_keys:
            raise DataValidationFailed("Missing keys '%s' for operation '%s'" %
                                       (list(missing_keys), current_op))

    if modified:
        app_log.debug("PATCH will modify row")

    return (patch, modified)


@gen.coroutine
def get_current_row(resource_update, uri, schema, idl):

    # Get a JSON representation of the row to patch
    uri = get._get_uri(resource_update, schema, uri)
    row_json = yield get.get_row_json(resource_update.row,
                                      resource_update.table,
                                      schema, idl, uri, OVSDB_SCHEMA_CONFIG,
                                      with_empty_values=True)
    row_json = row_json[OVSDB_SCHEMA_CONFIG]

    app_log.debug("Pre-patch row_json -> %s" % row_json)

    raise gen.Return(row_json)


def apply_patch(patch, row_json, resource_update=None, schema=None):

    try:
        # Now apply the patch to the row's JSON representation
        patched_row_json = patch.apply(row_json)
    except jsonpatch.JsonPatchException as e:
        app_log.debug(e)
        # TODO better exception handling using the different
        # kinds of exceptions thrown by JsonPatch
        raise PatchOperationFailed("PATCH cannot be applied.")
    except JsonPointerException as e:
        app_log.debug(e)
        raise PatchOperationFailed("Invalid path within PATCH.")

    if resource_update is not None and schema is not None:
        app_log.debug("Post-patch pre-hack row_json -> %s" % patched_row_json)
        # TODO remove this ugly hack after fix in GET behavior is merged
        # (bug #127)
        patched_row_json = remove_empty_optional_columns(schema,
                                                         resource_update,
                                                         patched_row_json)
        app_log.debug("Post-patch post-hack row_json -> %s" % patched_row_json)

    return patched_row_json


def prepare_data(patch, patched_row_json, resource,
                 resource_update, schema, idl):

    # Verify final transaction data
    verified_data = verify.verify_data(patched_row_json, resource, schema,
                                       idl, REQUEST_TYPE_PATCH)

    app_log.debug("Verified data pre- move/remove fix-> %s" % verified_data)

    # Removed columns need to be filled with
    # "empty" values before sending to IDL
    verified_data = refill_removed_columns(patch, verified_data,
                                           resource_update, schema)

    return verified_data


def refill_removed_columns(patch, data, resource, schema):
    '''
    For PATCH_OP_REMOVE and PATCH_OP_MOVE operations,
    applying the patch actually removes keys from the
    JSON that gets sent to IDL, which accomplishes
    nothing when removing/moving an entire column.
    In order to clear a column's value, it is needed
    to write an empty list or dict in the column and
    send this to IDL. For IDL, an optional column is
    that with min set to 0, which either makes it a
    list (even if just of max 1) or a dict if a key
    value pair is defined.
    Finally, this has to be done after validating the
    data, as an optional value with an enum defined
    will fail validation in verify_config_data, as the
    empty list/dict is not an accepted value.
    '''

    patch_list = patch.patch

    config_keys = deepcopy(schema.ovs_tables[resource.table].config)
    references = schema.ovs_tables[resource.table].references
    for key in references:
        if references[key].category == OVSDB_SCHEMA_CONFIG:
            config_keys.update({key: references[key]})

    patch_fix_list = []
    for patch_op in patch_list:

        if patch_op[PATCH_KEY_OP] in (PATCH_OP_REMOVE, PATCH_OP_MOVE):

            # Paths are validated previously when creating the patch,
            # so it's guaranteed that the resource's target column is
            # the first element in a path like "/a/b/c", in this case "a"

            if patch_op[PATCH_KEY_OP] == PATCH_OP_REMOVE:
                column = patch_op[PATCH_KEY_PATH].split("/")[1]
            else:
                column = patch_op[PATCH_KEY_FROM].split("/")[1]

            # Set the "default" value
            default_value = []
            if config_keys[column].is_dict:
                default_value = {}

            # If the PATCH_OP_MOVE or PATCH_OP_REMOVE
            # operation was performed on an entire column,
            # this column is no longer in the data, so it's
            # added back with the default value.
            if column not in data:

                # Create and append PATCH_OP_ADD
                add_op = {}
                add_op[PATCH_KEY_OP] = PATCH_OP_ADD
                add_op[PATCH_KEY_PATH] = "/%s" % column
                add_op[PATCH_KEY_VALUE] = default_value
                patch_fix_list.append(add_op)

    try:
        patch_fix = jsonpatch.JsonPatch(patch_fix_list)
    except:
        raise DataValidationFailed("Malformed final JSON patch")

    # If there's at least one operation, apply the patch
    if patch_fix:
        app_log.debug("Refill empty columns patch %s" % patch_fix.to_string())
        return patch_fix.apply(data, in_place=True)
    else:
        return data


def remove_empty_optional_columns(schema, resource_update, data):
    '''
    This removes any optional column whose value is default
    For int, real, and string, the column is removed only
    if the default value is out of the column's rangeMax
    '''
    config_keys = schema.ovs_tables[resource_update.table].config
    for key in config_keys:
        if key in data and config_keys[key].is_optional:
            if getutils.is_empty_value(data[key]):
                del data[key]
    return data
