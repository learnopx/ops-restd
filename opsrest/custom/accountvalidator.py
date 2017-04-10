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

# Third party imports
from tornado.log import app_log

# Local imports
import opsrest.utils.userutils as userutils
from opsrest.constants import OLD_PASSWORD_KEY, NEW_PASSWORD_KEY
from opsrest.exceptions import DataValidationFailed, NotAuthenticated


class AccountValidator():

    def __validate_required_fields__(self, account_info):
        """
        Validate required data fields
        Raises an exception if missing data
        """

        if not hasattr(account_info.configuration, OLD_PASSWORD_KEY) or \
                account_info.configuration.password is None:
            error = "Attribute '%s' is required" % OLD_PASSWORD_KEY
            raise DataValidationFailed(error)

        if not hasattr(account_info.configuration, NEW_PASSWORD_KEY) or \
                account_info.configuration.new_password is None:
            error = "Attribute '%s' is required" % NEW_PASSWORD_KEY
            raise DataValidationFailed(error)

    def validate_update(self, username, account_info):
        """
        Validates required fields, verifies if the user
        exists, verifies that the user is not root and that belongs to
        ops_netop group
        Raises an exception if any error occurs
        """

        app_log.debug("Validating account info update...")

        self.__validate_required_fields__(account_info)

        if username and userutils.user_exists(username):
            # Avoid update a root user
            if username == "root":
                error = "Permission denied. Cannot update the root user."
                raise DataValidationFailed(error)
        else:
            raise NotAuthenticated
