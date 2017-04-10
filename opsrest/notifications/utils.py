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

from opsrest.notifications.constants import (
    SUBSCRIBER_NAME,
    SUBSCRIBER_TABLE
)


def is_resource_modified(row_track_info, seqno):
    return row_track_info.update_seqno > seqno


def is_resource_added(row_track_info, seqno):
    return row_track_info.create_seqno > seqno


def is_resource_deleted(row_track_info, seqno):
    return row_track_info.delete_seqno > seqno


def get_table_changes_from_idl(table, idl):
    """
    Returns the list of changes from the IDL for the given table name.
    """
    return idl.track_get(table)


def is_table_changed(table, idl):
    return True if get_table_changes_from_idl(table, idl) else False


def lookup_subscriber_by_name(idl, subscriber_name):
    return idl.index_to_row_lookup([subscriber_name], SUBSCRIBER_TABLE)
