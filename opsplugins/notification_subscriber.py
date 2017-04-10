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
from opsvalidator.base import BaseValidator
from opsvalidator import error
from opsvalidator.error import ValidationError
from opsrest.utils.utils import get_column_data_from_row
from opsrest.notifications.constants import (
    SUBSCRIBER_NAME,
    SUBSCRIBER_TABLE_LOWER,
    SUBSCRIBER_TYPE,
    SUBSCRIBER_TYPE_WS
)


class NotificationSubscriberValidator(BaseValidator):
    resource = SUBSCRIBER_TABLE_LOWER

    def _is_websocket_subscriber(self, subscriber_row):
        subscriber_type = get_column_data_from_row(subscriber_row,
                                                   SUBSCRIBER_TYPE)
        return subscriber_type == SUBSCRIBER_TYPE_WS

    def validate_deletion(self, validation_args):
        app_log.debug("Verifying if the subscriber can be deleted..")
        subscriber_row = validation_args.resource_row
        subscriber_name = get_column_data_from_row(subscriber_row,
                                                   SUBSCRIBER_NAME)

        if self._is_websocket_subscriber(subscriber_row):
            details = "Subscriber: %s. " % subscriber_name
            details += "Cannot explicitly delete WebSocket based subscriber"
            raise ValidationError(error.METHOD_PROHIBITED, details)

    def validate_modification(self, validation_args):
        if validation_args.is_new:
            app_log.debug("Verifying if the subscriber can be added..")
            subscriber_row = validation_args.resource_row
            subscriber_name = get_column_data_from_row(subscriber_row,
                                                       SUBSCRIBER_NAME)

            if self._is_websocket_subscriber(subscriber_row):
                details = "Subscriber: %s. " % subscriber_name
                details += "Cannot explicitly add WebSocket based subscriber"
                raise ValidationError(error.METHOD_PROHIBITED, details)
