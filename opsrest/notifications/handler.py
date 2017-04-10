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

from tornado.log import app_log
from opsrest import parse
from opsrest.get import (
    is_resource_type_collection,
    get_collection_json,
    get_column_json
)
from opsrest.utils import utils
from opsrest.constants import (
    CHANGES_CB_TYPE,
    OVSDB_SCHEMA_BACK_REFERENCE,
    OVSDB_SCHEMA_TOP_LEVEL
)
from opsrest.handlers.websocket.notifications import WSNotificationsHandler
from opsrest.notifications import utils as notifutils
from opsrest.notifications import constants as consts
from opsrest.notifications.subscription import (
    CollectionSubscription,
    RowSubscription
)
from opsrest.notifications.exceptions import (
    NotificationException,
    NotificationMismatch,
    SubscriptionInvalidResource
)
from opsrest.notifications.monitor import OvsdbNotificationMonitor
from opsrest.notifications.utils import lookup_subscriber_by_name
from tornado import gen


class NotificationHandler():
    def __init__(self, schema, manager):
        self._subscriptions_by_table = {}
        self._subscriptions = {}
        self._schema = schema

        # Register for callbacks for subscription changes
        self._manager = manager
        self._subscriber_idl = self._manager.idl
        manager.add_callback(CHANGES_CB_TYPE,
                             self.subscription_changes_check_callback)

        # Enable monitoring for the subscription table
        self._manager.idl.track_add_all_columns(consts.SUBSCRIPTION_TABLE)

        # Register for callbacks for notifications of subscribed changes

        # TODO: When there is a better way to manage second monitor, reenable.
        # Currently reconnect times are too long and are too prone to missing
        # notifications. Currently, it causes problems. For now, reuse monitor
        # and add the callback to the manager. When this code is reenabled,
        # remove the callback added to the manager.
        # self._notification_monitor = \
        #    OvsdbNotificationMonitor(manager.remote,
        #                             manager.schema,
        #                             self._schema,
        #                             self.subscribed_changes_callback)

        # TODO: Remove this code when second monitor is enabled
        self._manager.add_callback(CHANGES_CB_TYPE,
                                   self.subscribed_changes_callback)

    @gen.coroutine
    def create_subscription(self, subscription_name, subscription_row,
                            resource_uri, idl):
        app_log.debug("Creating subscription for %s with URI %s" %
                      (subscription_name, resource_uri))

        resource = parse.parse_url_path(resource_uri, self._schema, idl)

        if resource is None:
            raise SubscriptionInvalidResource("Invalid resource URI " +
                                              resource_uri)

        # Get the subscription's URI
        subscriber_ref_col = \
            utils.get_parent_column_ref(consts.SUBSCRIBER_TABLE,
                                        consts.SUBSCRIPTION_TABLE,
                                        self._schema)

        subscriber_row, unused_value = \
            utils.get_parent_row(consts.SUBSCRIBER_TABLE,
                                 subscription_row,
                                 subscriber_ref_col,
                                 self._schema, idl)

        subscription_uri = utils.get_reference_uri(consts.SUBSCRIPTION_TABLE,
                                                   subscription_row,
                                                   self._schema, idl)

        # Get the last resource while preserving the parent resource.
        # None parent resource indicates the System table.
        parent_resource = None
        while resource.next is not None:
            parent_resource = resource
            resource = resource.next

        subscriber_name = self._get_subscriber_name(subscriber_row, idl)

        subscription = None
        if parent_resource and is_resource_type_collection(parent_resource):
            row_uuids = self.get_collection_row_uuids(parent_resource, idl)
            uris = yield get_collection_json(parent_resource, self._schema,
                                             idl, resource_uri, None, 0)

            if isinstance(uris, dict):
                uris = uris.values()

            rows_to_uri = dict(zip(row_uuids, uris))

            subscription = CollectionSubscription(resource.table,
                                                  subscriber_name,
                                                  subscription_uri,
                                                  resource_uri,
                                                  rows_to_uri)
        else:
            subscription = RowSubscription(resource.table, subscriber_name,
                                           subscription_uri, resource_uri,
                                           resource.row)

        raise gen.Return(subscription)

    def get_collection_row_uuids(self, parent_resource, idl):
        row_uuids = []

        if parent_resource.relation == OVSDB_SCHEMA_BACK_REFERENCE:
            parent_row = idl.tables[parent_resource.table].rows[parent_resource.row]
            parent_table = parent_resource.table
            child_table = parent_resource.next.table
            if parent_resource.next.row is None:
                rows = utils.get_back_reference_children(parent_row, parent_table,
                                                         child_table, self._schema, idl)
                for row in rows:
                    row_uuids.append(row.uuid)
            else:
                row_uuids.append(parent_resource.next.row)

        elif parent_resource.relation == OVSDB_SCHEMA_TOP_LEVEL:
            row_uuids = idl.tables[parent_resource.next.table].rows.keys()

        else:
            rows = utils.get_column_data_from_resource(parent_resource,
                                                       idl)

            # Check if column is of KV type. If so, retrieve the row UUIDs
            parent_schema = self._schema.ovs_tables[parent_resource.table]
            if parent_schema.references[parent_resource.column].kv_type:
                rows = rows.values()

            # Convert to UUIDs
            for row in rows:
                row_uuids.append(row.uuid)

        return row_uuids

    @gen.coroutine
    def get_ref_rows_to_uri_mapping_from_parent(self, ref_rows, parent_table,
                                                parent_row_uuid, idl,
                                                ref_column):
        rows_to_uri = {}
        if ref_rows:
            # Check if column is of KV type. If so, retrieve the row UUIDs
            parent_schema = self._schema.ovs_tables[parent_table]
            if parent_schema.references[ref_column].kv_type:
                ref_rows = ref_rows.values()

            # Convert to UUIDs
            row_uuids = []
            for row in ref_rows:
                row_uuids.append(row.uuid)

            parent_row = idl.tables[parent_table].rows[parent_row_uuid]
            parent_uri = utils.get_reference_uri(parent_table, parent_row,
                                                 self._schema, idl)

            resource_uris = yield get_column_json(ref_column, parent_row_uuid,
                                                  parent_table, self._schema,
                                                  idl, parent_uri)

            rows_to_uri = dict(zip(row_uuids, resource_uris))

        raise gen.Return(rows_to_uri)

    @gen.coroutine
    def subscription_changes_check_callback(self, manager, idl):
        """
        Callback method invoked by manager of the IDL used for detecting
        notification subscription changes.
        """
        table_changes = \
            notifutils.get_table_changes_from_idl(consts.SUBSCRIPTION_TABLE,
                                                  idl)

        for sub_uuid, sub_changes in table_changes.iteritems():
            seqno = manager.curr_seqno

            if notifutils.is_resource_added(sub_changes, seqno):
                subscription_row = \
                    idl.tables[consts.SUBSCRIPTION_TABLE].rows[sub_uuid]

                subscription_name = \
                    utils.get_table_key(subscription_row,
                                        consts.SUBSCRIPTION_TABLE,
                                        self._schema, idl)

                # Only one key, so grab the first index
                subscription_name = subscription_name[0]

                app_log.debug("Subscription added for: \"%s\"" %
                              subscription_name)

                resource_uri = \
                    utils.get_column_data_from_row(subscription_row,
                                                   consts.SUBSCRIPTION_URI)

                try:
                    subscription = \
                        yield self.create_subscription(subscription_name,
                                                       subscription_row,
                                                       resource_uri,
                                                       idl)

                    yield self.get_initial_values_and_notify(idl, subscription)
                    self.add_subscription(sub_uuid, subscription)
                except Exception as e:
                    app_log.error("Error while creating subscription: %s" % e)

            elif notifutils.is_resource_deleted(sub_changes, seqno):
                app_log.debug("Subscription was deleted.")
                self.remove_subscription(sub_uuid)

    @gen.coroutine
    def subscribed_changes_callback(self, manager, idl):
        subscriber_notifications = {}

        for table, subscriptions in self._subscriptions_by_table.iteritems():
            if not notifutils.is_table_changed(table, idl):
                continue

            app_log.debug("Detected changes to subscribed table \"%s\"" %
                          table)

            for subscription in subscriptions:
                subs_name = subscription.subscriber_name

                if subs_name not in subscriber_notifications:
                    subscriber_notifications[subs_name] = {}

                try:
                    sub = subscriber_notifications[subs_name]
                    added, modified, deleted = \
                        yield subscription.get_changes(manager, idl,
                                                       self._schema)

                    self._add_updates(sub, consts.UPDATE_TYPE_ADDED, added)
                    self._add_updates(sub, consts.UPDATE_TYPE_MODIFIED,
                                      modified)
                    self._add_updates(sub, consts.UPDATE_TYPE_DELETED, deleted)

                except NotificationMismatch as e:
                    app_log.debug(e.details)
                except NotificationException as e:
                    app_log.error("Error processing notification."
                                  "Error: %s" % e.details)

        for subscriber_name, changes in subscriber_notifications.iteritems():
            self.notify_subscriber(subscriber_name, changes,
                                   self._subscriber_idl)

    @gen.coroutine
    def get_initial_values_and_notify(self, idl, subscription):
        notify_msg = {}
        initial_values = yield subscription.get_initial_values(idl,
                                                               self._schema)

        if initial_values:
            self._add_updates(notify_msg, consts.UPDATE_TYPE_ADDED,
                              initial_values)
            self.notify_subscriber(subscription.subscriber_name, notify_msg,
                                   idl)

    def notify_subscriber(self, subscriber_name, changes, idl):
        if not changes:
            app_log.debug("No changes. Skip notification")
            return

        app_log.debug("Notifying subscriber %s." % subscriber_name)
        subscriber_row = lookup_subscriber_by_name(idl, subscriber_name)

        if subscriber_row:
            subscriber_type = self._get_subscriber_type(subscriber_row, idl)

            if subscriber_type == consts.SUBSCRIBER_TYPE_WS:
                notif_msg = {consts.NOTIF_MSG: changes}
                WSNotificationsHandler.send_notification_msg(subscriber_name,
                                                             notif_msg)
            else:
                app_log.error("Unsupported subscriber type: %s" %
                              subscriber_type)

    def add_subscription(self, subscription_uuid, subscription):
        app_log.debug("Adding subscription: %s\n%s" %
                      (subscription_uuid, subscription))

        # If the table is not already monitored in the IDL, need to
        # begin monitoring it.
        if subscription.table not in self._subscriptions_by_table:
            self._subscriptions_by_table[subscription.table] = set([])

            # TODO: Reenable this when second monitor is available.
            # self._notification_monitor.add_table_monitor(subscription.table)

            # TODO: Remove this when second monitor is available.
            self._manager.idl.track_add_all_columns(subscription.table)

        self._subscriptions_by_table[subscription.table].add(subscription)

        # Add the subscription by name for reverse lookup
        self._subscriptions[subscription_uuid] = subscription

    def remove_subscription(self, subscription_uuid):
        app_log.debug("Removing subscription %s" % subscription_uuid)

        subscription = None
        if subscription_uuid in self._subscriptions:
            subscription = self._subscriptions[subscription_uuid]

            del self._subscriptions[subscription_uuid]

        # Remove the subscription from the table map if it exists
        if subscription and subscription.table in self._subscriptions_by_table:
            table = subscription.table
            self._subscriptions_by_table[table].discard(subscription)

            # If the table is no longer being monitored, remove tracking and
            # monitoring from the idl.
            if not self._subscriptions_by_table[table]:
                # No longer need the table entry in the mapping.
                del self._subscriptions_by_table[table]

                # TODO: Reeable this when second monitor is available
                # Need to also remove tracking/monitoring
                # self._notification_monitor.remove_table_monitor(table)

                # TODO: Remove this when second monitor is available
                self._manager.idl.track_remove_all_columns(subscription.table)

    def _add_updates(self, subscriber_changes, update_type, updates):
        if not updates:
            return

        if update_type not in subscriber_changes:
            subscriber_changes[update_type] = []

        if not isinstance(updates, list):
            updates = [updates]

        for update in updates:
            subscriber_changes[update_type].append(update)

    def _get_subscriber_type(self, subscriber_row, idl):
        return utils.get_column_data_from_row(subscriber_row,
                                              consts.SUBSCRIBER_TYPE)

    def _get_subscriber_name(self, subscriber_row, idl):
        return utils.get_column_data_from_row(subscriber_row,
                                              consts.SUBSCRIBER_NAME)
