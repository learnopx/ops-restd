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

from opsrest.manager import OvsdbConnectionManager
from tornado.log import app_log
from opsrest.constants import CHANGES_CB_TYPE, ESTABLISHED_CB_TYPE


class OvsdbNotificationMonitor:
    def __init__(self, remote, schema, rest_schema, notification_callback):
        self.remote = remote
        self.schema = schema
        self.rest_schema = rest_schema
        self.tables_monitored = set([])
        self.manager = None
        self.notify_cb = notification_callback
        self.established = False

    def add_table_monitor(self, table):
        app_log.debug("Adding monitoring for table %s" % table)

        if table not in self.tables_monitored:
            self.tables_monitored.add(table)
            self.restart_monitoring()

    def remove_table_monitor(self, table):
        app_log.debug("Removing monitoring for table %s" % table)

        if table in self.tables_monitored:
            self.tables_monitored.discard(table)
            self.restart_monitoring()

    def restart_monitoring(self):
        app_log.debug("Restarting monitor..")

        if self.manager:
            # Check if there are any pending changes and notify before stopping
            if self.established:
                self.manager.idl_check_and_update()
                self.established = False

            self.manager.stop()

        self.manager = self.start_new_manager()

    def new_monitor_started_callback(self, manager, idl):
        app_log.debug("New monitor/manager started.")
        self.established = True

    def start_new_manager(self):
        app_log.debug("Starting new manager")

        manager = OvsdbConnectionManager(self.remote, self.schema,
                                         self.rest_schema)
        manager.start(self.tables_monitored, True)

        # Add callback for detecting changes to subscribed resources
        manager.add_callback(CHANGES_CB_TYPE, self.notify_cb)

        # Add callback for detecting when the manager's connection is
        # established
        manager.add_callback(ESTABLISHED_CB_TYPE,
                             self.new_monitor_started_callback)
        return manager
