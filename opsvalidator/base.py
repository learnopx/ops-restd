from tornado.log import app_log


class ValidationArgs(object):
    """
    Arguments from the validation framework used by validators
    """
    def __init__(self, idl, schema, table_name, row,
                 p_table_name, p_row, is_new):
        # General arguments
        self.idl = idl
        self.schema = schema
        self.is_new = is_new

        # Arguments specific to parent/child
        if p_table_name is not None:
            self.p_resource_table = p_table_name
            self.p_resource_schema = schema.ovs_tables[p_table_name]
            self.p_resource_idl_table = idl.tables[p_table_name]
            self.p_resource_row = p_row

        self.resource_table = table_name
        self.resource_schema = schema.ovs_tables[table_name]
        self.resource_idl_table = idl.tables[table_name]
        self.resource_row = row


class BaseValidator(object):
    """
    Base class for validators to provide as a hook and registration
    mechanism. Derived classes will be registered as validators.

    resource: Used for registering a validator with a resource/table name.
              It is used for validator lookup. Derived classes must define
              a value for proper registration/lookup.
    """
    resource = ""

    def type(self):
        return self.__class__.__name__

    def validate_modification(self, validation_args):
        app_log.debug("validate_modification not implemented for " +
                      self.type())

    def validate_deletion(self, validation_args):
        app_log.debug("validate_deletion not implemented for " + self.type())
