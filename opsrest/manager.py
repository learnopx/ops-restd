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

import time
from tornado.ioloop import IOLoop
from tornado.log import app_log

from ovs.db import error
from ovs.db.idl import SchemaHelper

from ops.opsidl import OpsIdl
from opsrest.transaction import OvsdbTransactionList, OvsdbTransaction
from opsrest.constants import (
    CHANGES_CB_TYPE,
    ESTABLISHED_CB_TYPE,
    OVSDB_DEFAULT_CONNECTION_TIMEOUT,
    INCOMPLETE
)
from opslib.restparser import ON_DEMAND_FETCHED_TABLES


class OvsdbConnectionManager:
    def __init__(self, remote, schema, rest_schema, *args, **kwargs):
        self.timeout = OVSDB_DEFAULT_CONNECTION_TIMEOUT
        self.remote = remote
        self.schema = schema
        self.rest_schema = rest_schema
        self.schema_helper = None
        self.idl = None
        self.transactions = None
        self.curr_seqno = 0
        self.connected = False
        self._callbacks = {}
        self._callbacks[CHANGES_CB_TYPE] = set()
        self._callbacks[ESTABLISHED_CB_TYPE] = set()
        self.timeout_handle = None
        self.ovs_socket = None
        self.register_tables = None
        self.track_all = False
        self.txn_timeout_handle = None

    def start(self, register_tables=None, track_all=False):
        try:
            app_log.info("Starting Connection Manager!")

            # Ensure stopping of any existing connection
            self.stop()
            self.schema_helper = SchemaHelper(self.schema)

            # Store registration and tracking info in case initial
            # connection is unsuccessful. If initial connection is unsuccesful,
            # the timeout callback will cause register_tables and track_all
            # to be None.
            if register_tables is not None:
                self.register_tables = register_tables
            if track_all is not False:
                self.track_all = track_all

            if not self.register_tables:
                self.register_schema_helper_columns(self.schema_helper,
                                                    self.rest_schema)
            else:
                for table in self.register_tables:
                    self.schema_helper.register_table(str(table))

            self.idl = OpsIdl(self.remote, self.schema_helper)
            self.curr_seqno = self.idl.change_seqno

            if self.track_all:
                app_log.debug("Tracking all changes")
                self.idl.track_add_all()

            # We do not reset transactions when the DB connection goes down
            if self.transactions is None:
                self.transactions = OvsdbTransactionList()

            self.idl_init()

        except Exception as e:
            app_log.info("Connection Manager failed! Reason: %s" % e)
            self.timeout_handle = \
                IOLoop.current().add_timeout(time.time() + self.timeout,
                                             self.start)

    def stop(self):
        if self.ovs_socket:
            IOLoop.current().remove_handler(self.ovs_socket)
            self.ovs_socket = None

        if self.timeout_handle:
            IOLoop.current().remove_timeout(self.timeout_handle)
            self.timeout_handle = None

        self.stop_transaction_timer()

        if self.idl:
            self.idl.close()
            self.idl = None

    def idl_init(self):
        try:
            self.idl.run()
            if not self.idl.has_ever_connected():
                app_log.debug("ovsdb unavailable retrying")
                self.timeout_handle = \
                    IOLoop.current().add_timeout(time.time() + self.timeout,
                                                 self.idl_init)
            else:
                self.idl_establish_connection()
        except error.Error as e:
            # idl will raise an error exception if cannot connect
            app_log.debug("Failed to connect, retrying. Reason: %s" % e)
            self.timeout_handle = \
                IOLoop.current().add_timeout(time.time() + self.timeout,
                                             self.idl_init)

    def idl_reconnect(self):
        try:
            app_log.debug("Trying to reconnect to ovsdb")
            # Idl run will do the reconnection
            self.idl.run()
            # If the seqno change the ovsdb connection is restablished.
            if self.curr_seqno == self.idl.change_seqno:
                app_log.debug("ovsdb unavailable retrying")
                self.connected = False
                self.timeout_handle = \
                    IOLoop.current().add_timeout(time.time() + self.timeout,
                                                 self.idl_reconnect)
            else:
                self.idl_establish_connection()
        except error.Error as e:
            # idl will raise an error exception if cannot reconnect
            app_log.debug("Failed to connect, retrying. Reason: %s" % e)
            self.timeout_handle = \
                IOLoop.current().add_timeout(time.time() + self.timeout,
                                             self.idl_reconnect)

    def idl_establish_connection(self):
        app_log.info("ovsdb connection ready")
        self.connected = True
        self.curr_seqno = self.idl.change_seqno
        self.ovs_socket = self.idl._session.rpc.stream.socket
        IOLoop.current().add_handler(self.ovs_socket.fileno(),
                                     self.idl_run,
                                     IOLoop.READ | IOLoop.ERROR)

        self.run_callbacks(ESTABLISHED_CB_TYPE)

    def idl_check_and_update(self):
        self.idl.run()

        if self.curr_seqno != self.idl.change_seqno:
            self.run_callbacks(CHANGES_CB_TYPE)

            if len(self.transactions.txn_list):
                self.check_transactions()

        self.curr_seqno = self.idl.change_seqno

    def idl_run(self, fd=None, events=None):
        if events & IOLoop.ERROR:
            app_log.debug("Socket fd %s error" % fd)
            if fd is not None:
                IOLoop.current().remove_handler(fd)
                self.idl_reconnect()
        elif events & IOLoop.READ:
            self.idl_check_and_update()

    def check_transactions(self):
        self.stop_transaction_timer()
        txn_incomplete = False

        for index, tx in enumerate(self.transactions.txn_list):
            tx.commit()
            # TODO: Handle all states
            if tx.status is not INCOMPLETE:
                self.transactions.txn_list.pop(index)
                tx.event.set()
            else:
                txn_incomplete = True

        if txn_incomplete:
            self.start_transaction_timer()

    def get_new_transaction(self):
        return OvsdbTransaction(self.idl)

    def monitor_transaction(self, txn):
        self.transactions.add_txn(txn)
        self.start_transaction_timer()

    def stop_transaction_timer(self):
        if self.txn_timeout_handle:
            IOLoop.current().remove_timeout(self.txn_timeout_handle)
            self.txn_timeout_handle = None

    def start_transaction_timer(self):
        if not self.txn_timeout_handle:
            self.txn_timeout_handle = \
                IOLoop.current().add_timeout(time.time() + self.timeout,
                                             self.check_transactions)

    def add_callback(self, cb_type, callback):
        if cb_type in self._callbacks:
            self._callbacks[cb_type].add(callback)

    def remove_callback(self, cb_type, callback):
        if cb_type in self._callbacks:
            self._callbacks[cb_type].discard(callback)

    def run_callbacks(self, cb_type):
        if cb_type in self._callbacks:
            for callback in self._callbacks[cb_type]:
                callback(self, self.idl)

            # Clear any change tracking info received for next notifications
            if cb_type == CHANGES_CB_TYPE:
                self.idl.track_clear_all()

    def register_schema_helper_columns(self, schema_helper, ext_schema):
        app_log.debug("Registering schema helper columns..")

        for table_name, table_schema in ext_schema.ovs_tables.iteritems():
            if table_name in ON_DEMAND_FETCHED_TABLES:
                schema_helper.register_columns(str(table_name),
                                               table_schema.columns,
                                               table_schema.readonly_columns)
            else:
                schema_helper.register_table(str(table_name))
