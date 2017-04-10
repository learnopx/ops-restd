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

from opsrest.utils.utils import (
    get_reference_uri,
    row_ovs_column_to_json
)
from opsrest.get import get_row_json, get_column_json
from opsrest.notifications.utils import (
    get_table_changes_from_idl,
    is_resource_added,
    is_resource_deleted,
    is_resource_modified
)
from opsrest.notifications.constants import (
    NOTIF_SUBSCRIPTION_FIELD,
    NOTIF_RESOURCE_FIELD,
    NOTIF_NEW_VALUES_FIELD,
    NOTIF_VALUES_FIELD
)
from opsrest.notifications.exceptions import (
    NotificationMismatch,
    NotificationValueError
)
from tornado.log import app_log
from tornado import gen


def construct_modified_msg(subscription_uri, resource_uri, changes):
    modified = {NOTIF_SUBSCRIPTION_FIELD: subscription_uri,
                NOTIF_RESOURCE_FIELD: resource_uri,
                NOTIF_NEW_VALUES_FIELD: changes}
    return modified


def construct_added_msg(subscription_uri, resource_uri, values):
    added = {NOTIF_SUBSCRIPTION_FIELD: subscription_uri,
             NOTIF_RESOURCE_FIELD: resource_uri,
             NOTIF_VALUES_FIELD: values}
    return added


def construct_deleted_msg(subscription_uri, resource_uri):
    deleted = {NOTIF_SUBSCRIPTION_FIELD: subscription_uri,
               NOTIF_RESOURCE_FIELD: resource_uri}
    return deleted


@gen.coroutine
def get_row_initial_values(row, table, schema, idl, resource_uri,
                           subscription_uri):
    resource_data = yield get_row_json(row, table, schema, idl, resource_uri)

    # Remove categories returned by get_row_json
    columns_to_values = {}
    for category, column_data in resource_data.iteritems():
        columns_to_values.update(column_data)

    raise gen.Return(construct_added_msg(subscription_uri, resource_uri,
                                         columns_to_values))


class Subscription(object):
    def __init__(self, table, subscriber_name, subscription_uri):
        self.table = table
        self.subscriber_name = subscriber_name
        self.subscription_uri = subscription_uri

    def get_initial_values(self, idl, schema):
        pass

    def get_changes(self, manager, idl, schema):
        pass

    def __str__(self):
        info_str = "Table: %s\n" % self.table
        info_str += "Subscriber Name: %s\n" % self.subscriber_name
        info_str += "Subscription URI: %s\n" % self.subscription_uri
        return info_str


class RowSubscription(Subscription):
    def __init__(self, table, subscriber_name, subscription_uri,
                 resource_uri, row):
        super(RowSubscription, self).__init__(table, subscriber_name,
                                              subscription_uri)

        # Resource URI as provided in the subscription
        self.resource_uri = resource_uri
        self.row = row

    @gen.coroutine
    def get_initial_values(self, idl, schema):
        values = yield get_row_initial_values(self.row, self.table, schema,
                                              idl, self.resource_uri,
                                              self.subscription_uri)
        raise gen.Return(values)

    @gen.coroutine
    def get_changes(self, manager, idl, schema):
        deleted = None
        modified = None

        # Check if current subscription is in the list of changes
        table_changes = get_table_changes_from_idl(self.table, idl)
        if self.row not in table_changes:
            raise NotificationMismatch("Row not found in changes.")

        row_change_info = table_changes[self.row]

        # Check if it was deleted or modified
        if is_resource_modified(row_change_info, manager.curr_seqno):
            updated_cols = row_change_info.columns
            columns_to_values = yield self.get_columns_to_values(updated_cols,
                                                                 idl, schema)
            modified = construct_modified_msg(self.subscription_uri,
                                              self.resource_uri,
                                              columns_to_values)
        elif is_resource_deleted(row_change_info, manager.curr_seqno):
            deleted = construct_deleted_msg(self.subscription_uri,
                                            self.resource_uri)
        else:
            raise NotificationMismatch("No changes detected")

        raise gen.Return((None, modified, deleted))

    @gen.coroutine
    def get_columns_to_values(self, columns, idl, schema):
        column_to_values = {}
        schema_table = schema.ovs_tables[self.table]

        for column in columns:
            data = None

            if column in schema_table.references:
                data = yield get_column_json(column, self.row, self.table,
                                             schema, idl, self.resource_uri)
            else:
                ovs_column = None

                if column in schema_table.config:
                    ovs_column = schema_table.config[column]
                elif column in schema_table.stats:
                    ovs_column = schema_table.stats[column]
                elif column in schema_table.status:
                    ovs_column = schema_table.status[column]
                else:
                    raise NotificationValueError("Attribute not found")

                resource_row = idl.tables[self.table].rows[self.row]
                data = row_ovs_column_to_json(resource_row, ovs_column)

            column_to_values[column] = data

        raise gen.Return(column_to_values)

    def __str__(self):
        info_str = super(RowSubscription, self).__str__()
        info_str += "Resource URI: %s\n" % self.resource_uri
        info_str += "Row: %s\n" % self.row
        return info_str


class CollectionSubscription(Subscription):
    def __init__(self, table, subscriber_name, subscription_uri,
                 collection_uri, rows_to_uri):
        super(CollectionSubscription, self).__init__(table, subscriber_name,
                                                     subscription_uri)
        self.collection_uri = collection_uri

        # URI to the collection as a list
        self.uri_segments = collection_uri.split('/')

        # Rows to be monitored as a part of the collection. Initially
        # populated with the rows currently in the DB.
        self.rows_to_uri = rows_to_uri

    @gen.coroutine
    def get_initial_values(self, idl, schema):
        initial_values = []

        for row_uuid, resource_uri in self.rows_to_uri.iteritems():
            data = yield get_row_initial_values(row_uuid, self.table, schema,
                                                idl, resource_uri,
                                                self.subscription_uri)

            if data:
                initial_values.append(data)

        raise gen.Return(initial_values)

    @gen.coroutine
    def get_changes(self, manager, idl, schema):
        table_changes = get_table_changes_from_idl(self.table, idl)
        added = []
        deleted = []

        for row_uuid, row_change_info in table_changes.iteritems():
            # Check for additions
            if is_resource_added(row_change_info, manager.curr_seqno):
                app_log.debug("Detected new resource added to collection")

                row = idl.tables[self.table].rows[row_uuid]

                # Since added, need to check if it's part of the subscribed
                # collection URI. Get URI trace for this resource.
                resource_uri = get_reference_uri(self.table, row, schema, idl)
                uri_trace = resource_uri.split('/')

                app_log.debug("URI of added resource retrieved: %s" %
                              resource_uri)

                # Lengths of the resource URI should be greater than the
                # collection's URI.
                if len(uri_trace) < len(self.uri_segments):
                    raise NotificationMismatch("URI not a part of "
                                               "the collection. Skip.")

                for idx, segment in enumerate(self.uri_segments):
                    # TODO: In the future, for wildcards, also check for *
                    if segment != uri_trace[idx]:
                        # This resource change is not a part of a subscribed
                        # collection.
                        app_log.debug("Parents did not match. %s != %s" %
                                      (segment, uri_trace[idx]))
                        raise NotificationMismatch("Subscription mismatch.")

                # Add new entry
                self.rows_to_uri[row_uuid] = resource_uri

                added_data = \
                    yield get_row_initial_values(row_uuid, self.table,
                                                 schema, idl,
                                                 resource_uri,
                                                 self.subscription_uri)

                added.append(added_data)

            elif is_resource_deleted(row_change_info, manager.curr_seqno):
                app_log.debug("Detected resource deleted from collection")

                # Check if it's part of a collection that we were tracking
                if row_uuid in self.rows_to_uri:
                    app_log.debug("Row found in subscription.")

                    # Grab the resource URI before it's deleted.
                    data = construct_deleted_msg(self.subscription_uri,
                                                 self.rows_to_uri[row_uuid])
                    deleted.append(data)
                    del self.rows_to_uri[row_uuid]
            else:
                raise NotificationMismatch("No changes detected")

        raise gen.Return((added, None, deleted))

    def __str__(self):
        info_str = super(CollectionSubscription, self).__str__()
        info_str += "Collection URI: %s\n" % self.collection_uri
        info_str += "Rows: %s\n" % self.rows_to_uri
        return info_str
