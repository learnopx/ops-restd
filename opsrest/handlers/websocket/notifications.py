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

import json
from tornado import gen
from tornado.log import app_log
from opsrest.utils import utils
from opsrest.constants import (
    ERROR,
    INCOMPLETE,
    OVSDB_BASE_URI,
    SUCCESS
)
from opsrest.notifications.constants import (
    SUBSCRIBER_NAME,
    SUBSCRIBER_OPEN_ERROR,
    SUBSCRIBER_TABLE,
    SUBSCRIBER_TABLE_LOWER,
    SUBSCRIBER_TYPE,
    SUBSCRIBER_TYPE_WS,
    WS_RESOURCE_URI
)
from opsrest.notifications.utils import lookup_subscriber_by_name
from opsrest.handlers.websocket.base import WSBaseHandler


class WSNotificationsHandler(WSBaseHandler):
    def initialize(self, ref_object):
        super(WSNotificationsHandler, self).initialize(ref_object)

    @staticmethod
    def send_notification_msg(sub_name, msg):
        ws = WSBaseHandler.get_websocket(sub_name)

        if not ws:
            app_log.error("Websocket not found. Couldn't send notification.")
            return

        ws.send_message(json.dumps(msg))

    def _generate_id(self):
        """
        Overridden method for generating ID. Ensure subscriber doesn't already
        exist with the same name/ID.
        """
        while True:
            new_id = super(WSNotificationsHandler, self).generate_id()

            # Make sure a subscriber with the same name doesn't already exist
            # in the DB
            if not lookup_subscriber_by_name(self.idl, new_id):
                break

        return new_id

    @gen.coroutine
    def _open(self):
        txn = self.manager.get_new_transaction()
        subscriber_data = {}
        subscriber_data[SUBSCRIBER_NAME] = self.id
        subscriber_data[SUBSCRIBER_TYPE] = SUBSCRIBER_TYPE_WS

        subscriber_row = utils.setup_new_row(SUBSCRIBER_TABLE,
                                             subscriber_data,
                                             self.schema, txn, self.idl)
        status = ERROR

        if subscriber_row:
            status = txn.commit()
            if status == INCOMPLETE:
                self.manager.monitor_transaction(txn)
                yield txn.event.wait()
                status = txn.status

        if status == SUCCESS:
            app_log.debug("Subscriber \"%s\" added." % self.id)
            subscriber_table = self.schema.ovs_tables[SUBSCRIBER_TABLE]
            subscriber_uri = OVSDB_BASE_URI + subscriber_table.plural_name
            subscriber_uri += '/' + self.id

            response = {
                SUBSCRIBER_TABLE_LOWER: {
                    WS_RESOURCE_URI: subscriber_uri
                }
            }

            self.write_message(json.dumps(response))
        else:
            app_log.error("Failed to add subscriber: %s" % status)
            txn.abort()
            self._handle_open_fail()

    @gen.coroutine
    def _on_close(self):
        # Remove the db entry only if it exists.
        subscriber = lookup_subscriber_by_name(self.idl, self.id)
        if subscriber:
            txn = self.manager.get_new_transaction()

            subscriber.delete()

            status = txn.commit()
            if status == INCOMPLETE:
                self.manager.monitor_transaction(txn)
                yield txn.event.wait()
                status = txn.status

            if status == SUCCESS:
                app_log.debug("Subscriber %s removed." % self.id)
            else:
                app_log.error("Error deleting subscriber: %s" % status)
                txn.abort()

    def _handle_open_fail(self):
        error = "Unable to create a new subscriber."
        failed_data = {SUBSCRIBER_TABLE_LOWER: {SUBSCRIBER_OPEN_ERROR: error}}
        app_log.error(error)

        self.write_message(json.dumps(failed_data))
        self.close()
