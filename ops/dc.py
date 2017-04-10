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

import _read, _write
import ops.constants, ops.opsidl

from ovs.db.idl import SchemaHelper, Idl, Transaction

import ovs.vlog
vlog = ovs.vlog.Vlog('dc')


def register(extschema, ovsschema, ovsremote):
    """Register interest in all configuration and index
    columns for all tables in ovsschema.

    Args:
        extschema (opslib.RestSchema): This is the
            parsed extended-schema (vswitch.extschema) object.
        ovsschema: OVSDB schema file
        ovsremote: OVSDB remote socket

    Returns:
        ovs.db.idl.Idl instance
    """

    schema_helper = SchemaHelper(ovsschema)

    for tablename, tableschema in extschema.ovs_tables.iteritems():

        register_columns = []

       # configuration columns
        config_columns = [str(key) for key in tableschema.config.keys()]
        # reference columns
        reference_columns = [str(key) for key in tableschema.references.keys()]

        # index columns
        for item in tableschema.index_columns:
            if not item in config_columns:
                register_columns.append(str(item))

        register_columns += config_columns
        register_columns += reference_columns

        # dynamic columns
        if tableschema.dynamic:
            for key in tableschema.dynamic.keys():
                if key not in register_columns:
                    register_columns.append(key)

        # NOTE: remove this when we have a proper
        # solution for TG-1116
        if str(tablename) == 'VLAN':
            register_columns.append('internal_usage')

        schema_helper.register_columns(str(tablename), register_columns)

    idl = ops.opsidl.OpsIdl(ovsremote, schema_helper)
    return idl


def read(extschema, idl):
    """Read the OpenSwitch OVSDB database

    Args:
        extschema (opslib.RestSchema): This is the
            parsed extended-schema (vswitch.extschema) object.
        idl (ovs.db.idl.Idl): This is the IDL object that
            represents the OVSDB IDL.

    Returns:
        dict: Returns a Python dictionary object containing
            data read from all OVSDB tables and arranged according
            to the relationship between various tables as
            described in vswitch.extschema
    """
    config = {}
    for table_name in extschema.ovs_tables.keys():

        # Check only root table or top level table
        if extschema.ovs_tables[table_name].parent is not None:
            continue

        # Get table data for root or top level table
        try:
            table_data = _read.get_table_data(table_name, extschema, idl)
        except Exception as e:
            vlog.err(e)
            return e

        if table_data is not None:
            config.update(table_data)

    # remove system uuid
    config[ops.constants.OVSDB_SCHEMA_SYSTEM_TABLE] = config[ops.constants.OVSDB_SCHEMA_SYSTEM_TABLE].values()[0]
    vlog.dbg('succcess generating running configuration')
    return config

def write(data, extschema, idl, txn=None, block=False):
    """Write a new configuration to OpenSwitch OVSDB database

    Args:
        data (dict): The new configuration represented as a Python
            dictionary object.
        extschema (opslib.RestSchema): This is the
            parsed extended-schema (vswitch.extschema) object.
        idl (ovs.db.idl.Idl): This is the IDL object that
            represents the OVSDB IDL.
        txn (ovs.db.idl.Transaction): OVSDB transaction object.
        block (boolean): if block is True, commit_block() is used

    Returns:
        result : The result of transaction commit
    """
    if txn is None:
        try:
            txn = Transaction(idl)
            block = True
        except AssertionError as e:
            vlog.dbg('error in creating transaction: %s' % e)
            return e

    # dc.read returns config db with 'System' table
    # indexed to 'System' keyword. Replace it with
    # current database's System row UUID so that all
    # tables in 'data' are represented the same way

    try:
        system_uuid = idl.tables[ops.constants.OVSDB_SCHEMA_SYSTEM_TABLE].rows.keys()[0]
        data[ops.constants.OVSDB_SCHEMA_SYSTEM_TABLE] = {system_uuid:data[ops.constants.OVSDB_SCHEMA_SYSTEM_TABLE]}

        _write.setup_validators(extschema, idl)

        # iterate over all top-level tables i.e. root
        for table_name, tableschema in extschema.ovs_tables.iteritems():

            # iterate over non-children tables
            if extschema.ovs_tables[table_name].parent is not None:
                continue

            # set up the non-child table
            _write.setup_table(table_name, data, extschema, idl, txn)

        # iterate over all tables to fill in references
        for table_name, tableschema in extschema.ovs_tables.iteritems():

            if extschema.ovs_tables[table_name].parent is not None:
                continue

            _write.setup_references(table_name, data, extschema, idl)

        validation_errors = _write.exec_validators()
        if validation_errors:
            return (txn.ERROR, validation_errors)

    except Exception as e:
        txn.abort()
        return (txn.ERROR, e)

    try:
        if not block:
            # txn maybe be incomplete
            result = txn.commit()
        else:
            # txn will block until it is completed
            result = txn.commit_block()
        vlog.dbg('transacton result: %s' % result)
        return (result, txn.get_error())

    except Exception as e:
        vlog.err('transaction exception: %s' % e)
        txn.abort()
        return (txn.ERROR, e)
