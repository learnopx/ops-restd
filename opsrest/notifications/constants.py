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

SUBSCRIBER_TABLE = "Notification_Subscriber"
SUBSCRIBER_TABLE_LOWER = SUBSCRIBER_TABLE.lower()
SUBSCRIPTION_TABLE = "Notification_Subscription"
SUBSCRIPTION_TABLE_LOWER = SUBSCRIPTION_TABLE.lower()

WS_RESOURCE_URI = "resource"

# Fields for a notification message
NOTIF_MSG = "notifications"
NOTIF_SUBSCRIPTION_FIELD = "subscription"
NOTIF_RESOURCE_FIELD = "resource"
NOTIF_VALUES_FIELD = "values"
NOTIF_NEW_VALUES_FIELD = "new_values"

# Notification update group types
UPDATE_TYPE_ADDED = "added"
UPDATE_TYPE_MODIFIED = "modified"
UPDATE_TYPE_DELETED = "deleted"

# Subscriber attributes
SUBSCRIBER_TYPE = "type"
SUBSCRIBER_TYPE_WS = "ws"
SUBSCRIBER_NAME = "name"

SUBSCRIBER_OPEN_ERROR = "error"

# Subscription attributes
SUBSCRIPTION_NAME = "name"
SUBSCRIPTION_URI = "resource"
