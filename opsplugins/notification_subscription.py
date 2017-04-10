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
    SUBSCRIPTION_TABLE_LOWER,
    SUBSCRIPTION_URI
)
from opsrest.constants import REQUEST_TYPE_READ
from opsrest.parse import parse_url_path


class NotificationSubscriptionValidator(BaseValidator):
    resource = SUBSCRIPTION_TABLE_LOWER

    def validate_modification(self, validation_args):
        if validation_args.is_new:
            schema = validation_args.schema
            idl = validation_args.idl
            subscriber_row = validation_args.p_resource_row
            subscription_row = validation_args.resource_row
            subscription_schema = validation_args.resource_schema

            subscriber_name = get_column_data_from_row(subscriber_row,
                                                       SUBSCRIBER_NAME)
            resource_uri = get_column_data_from_row(subscription_row,
                                                    SUBSCRIPTION_URI)

            app_log.debug("Verifying if subscription can be added for "
                          "subscriber %s" % subscriber_name)

            self._verify_duplicate_subscription(subscriber_name,
                                                subscriber_row,
                                                subscription_row,
                                                subscription_schema,
                                                resource_uri)

            self._verify_valid_resource_uri(subscriber_name, subscription_row,
                                            resource_uri, schema, idl)

    def _verify_valid_resource_uri(self, subscriber_name, subscription_row,
                                   resource_uri, schema, idl):
        app_log.debug("Verifying a valid resource URI")
        resource_path = parse_url_path(resource_uri, schema, idl,
                                       REQUEST_TYPE_READ)

        if resource_path is None:
            app_log.debug("Invalid resource URI detected")
            details = "Subscriber: %s. " % subscriber_name
            details += "Invalid URI %s" % resource_uri
            raise ValidationError(error.VERIFICATION_FAILED, details)

    def _verify_duplicate_subscription(self, subscriber_name, subscriber_row,
                                       subscription_row, subscription_schema,
                                       resource_uri):
        app_log.debug("Verifying if the subscription is a duplicate")
        subscriber_subscriptions = \
            get_column_data_from_row(subscriber_row,
                                     subscription_schema.plural_name)

        # Length == 1 indicates this is the only subscription
        if not subscriber_subscriptions or \
                len(subscriber_subscriptions) == 1:
            app_log.debug("No duplicate resource subscriptions detected.")
            return

        # Compare the resource URI of the new subscription to parent's
        # subscription resource URIs
        for sub_name, sub_row in subscriber_subscriptions.iteritems():
            # Skip if the subscription row is the current one that is
            # being validated
            if sub_row == subscription_row:
                continue

            curr_resource_uri = get_column_data_from_row(sub_row,
                                                         SUBSCRIPTION_URI)

            if curr_resource_uri == resource_uri:
                app_log.debug("Duplicate resource URI detected")
                details = "Subscriber: %s. " % subscriber_name
                details += "URI %s already exists" % resource_uri
                raise ValidationError(error.DUPLICATE_RESOURCE, details)
