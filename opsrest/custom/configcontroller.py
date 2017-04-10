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
from tornado import gen

# Local imports
import ops.dc
import ops.cfgd
from opsrest.exceptions import DataValidationFailed,\
    NotModified, InternalError, NotFound, APIException
from opsrest.transaction import OvsdbTransactionResult
from opsrest.custom.basecontroller import BaseController
from opsrest.constants import CONFIG_TYPE_RUNNING,\
    CONFIG_TYPE_STARTUP, SUCCESS, UNCHANGED, INCOMPLETE, ERROR


class ConfigController(BaseController):

    def initialize(self):
        self.idl = self.context.manager.idl
        self.schema = self.context.restschema
        self.txn = None

    @gen.coroutine
    def update(self, item_id, data, current_user, query_args):
        try:
            request_type = self.get_request_type(query_args)
            self.check_config_type(request_type)
            status = None
            error = None
            if request_type == CONFIG_TYPE_RUNNING:
                self.txn = self.context.manager.get_new_transaction()
                (status, error) = ops.dc.write(data, self.schema,
                                               self.idl, self.txn.txn)
                app_log.debug('Transaction result: %s', status)

                if status == INCOMPLETE:
                    self.context.manager.monitor_transaction(self.txn)
                    yield self.txn.event.wait()
                    status = self.txn.status
                    if status == ERROR:
                        error = self.txn.get_error()
            else:
                # FIXME: This is a blocking call.
                (status, error) = ops.cfgd.write(data)

            if status != SUCCESS:
                if status == UNCHANGED:
                    raise NotModified
                else:
                    if request_type == CONFIG_TYPE_RUNNING:
                        self.txn.abort()
                    raise APIException("Error: %s" % error)

        except Exception as e:
            if self.txn:
                self.txn.abort()
            raise APIException("Error: %s" % str(e))

    @gen.coroutine
    def get_all(self, current_user, selector, query_args):
        request_type = self.get_request_type(query_args)
        self.check_config_type(request_type)
        result = None
        if request_type == CONFIG_TYPE_RUNNING:
            result = ops.dc.read(self.schema, self.idl)
        else:
            # FIXME: This is a blocking call
            result = ops.cfgd.read()
        if result is None:
            if request_type == CONFIG_TYPE_RUNNING:
                raise InternalError
            else:
                raise NotFound
        return result

    def get_request_type(self, query_args):
        app_log.debug('Query args: %s', query_args)
        if not query_args:
            return CONFIG_TYPE_RUNNING
        else:
            typearg = query_args.get("type", CONFIG_TYPE_RUNNING)
            return typearg[0]

    def check_config_type(self, request_type):
        app_log.debug('Requested config type: %s', request_type)
        if request_type not in [CONFIG_TYPE_RUNNING, CONFIG_TYPE_STARTUP]:
            error = "Invalid configuration type. Configuration "\
                    "types allowed: %s, %s" %\
                    (CONFIG_TYPE_RUNNING, CONFIG_TYPE_STARTUP)
            raise DataValidationFailed(error)

    @gen.coroutine
    def get_patch(self, item_id=None, current_user=None, selector=None,
                  query_args=None):
        result = yield self.get_all(current_user, selector, query_args)
        raise gen.Return(result)
