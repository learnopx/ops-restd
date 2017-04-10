import ops.constants
from opsvalidator import validator
from opsvalidator.error import ValidationError

import ovs.vlog
vlog = ovs.vlog.Vlog('dc')


class ResourceOperationData(object):
    def __init__(self, method, resource_row, resource_table, p_resource_row,
                 p_resource_table):
        self.method = method
        self.resource_row = resource_row
        self.resource_table = resource_table
        self.p_resource_row = p_resource_row
        self.p_resource_table = p_resource_table


class ValidatorAdapter(object):
    """
    Adapter for the opsvalidator.validator module based on resource operations.
    """
    def __init__(self, extschema, idl):
        self.extschema = extschema
        self.idl = idl
        self.resource_ops_dict = {ops.constants.REQUEST_TYPE_CREATE: [],
                                  ops.constants.REQUEST_TYPE_UPDATE: [],
                                  ops.constants.REQUEST_TYPE_DELETE: []}
        self.errors = []
        validator.init_plugins(ops.constants.OPSPLUGIN_DIR)

    def has_errors(self):
        return len(self.errors) > 0

    def add_resource_op(self, op, resource_row, resource_table,
                        p_resource_row=None, p_resource_table=None):
        vlog.dbg("Adding operation - op: " + op + ", " +
                 "row: " + str(resource_row) + ", " +
                 "table: " + resource_table + ", " +
                 "parent row: " + str(p_resource_row) + ", " +
                 "parent table: " + str(p_resource_table))

        resource_op = ResourceOperationData(op, resource_row, resource_table,
                                            p_resource_row, p_resource_table)
        self.resource_ops_dict[op].append(resource_op)

    def _exec_validator_with_op(self, op_data):
        success = True
        method = op_data.method
        table_name = op_data.resource_table
        row = op_data.resource_row
        p_table_name = op_data.p_resource_table
        p_row = op_data.p_resource_row

        try:
            validator.exec_validators(self.idl, self.extschema, table_name,
                                      row, method, p_table_name, p_row)
        except ValidationError as e:
            vlog.dbg(str(e.error))
            self.errors.append(e.error)
            success = False

        except Exception as e:
            success = False

        return success

    def _exec_deletion_validators_and_delete(self):
        for delete_op_data in self.resource_ops_dict[ops.constants.REQUEST_TYPE_DELETE]:
            success = self._exec_validator_with_op(delete_op_data)

            # Delete the row from the IDL
            if success:
                delete_op_data.resource_row.delete()

    def _exec_modification_validators(self):
        for create_op_data in self.resource_ops_dict[ops.constants.REQUEST_TYPE_CREATE]:
            self._exec_validator_with_op(create_op_data)

        for update_op_data in self.resource_ops_dict[ops.constants.REQUEST_TYPE_UPDATE]:
            self._exec_validator_with_op(update_op_data)

    def exec_validators_with_ops(self):
        vlog.dbg("Executing validators for all ops..")
        # Deletion validations should occur first, since the deletions were
        # postponed in order to retain the row data for validations. Prior
        # to modification validations, the rows should actually be removed
        # from the IDL.
        self._exec_deletion_validators_and_delete()
        self._exec_modification_validators()
