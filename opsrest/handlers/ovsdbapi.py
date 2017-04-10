# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
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

from tornado import gen
from tornado.log import app_log

import json
import httplib

from opsrest.handlers import base
from opsrest.parse import parse_url_path
from opsrest.utils import utils
from opsrest.constants import *
from opsrest.exceptions import APIException, LengthRequired, \
    ParameterNotAllowed, DataValidationFailed
from opsrest.utils.getutils import get_filters_args


from opsrest import get, post, delete, put, patch


class OVSDBAPIHandler(base.BaseHandler):

    # parse the url and http params.
    @gen.coroutine
    def prepare(self):
        try:
            # Call parent's prepare to check authentication
            super(OVSDBAPIHandler, self).prepare()

            # Check ovsdb connection before each request
            if not self.ref_object.manager.connected:
                self.set_status(httplib.SERVICE_UNAVAILABLE)
                self.finish()

            self.resource_path = parse_url_path(self.request.path,
                                                self.schema,
                                                self.idl,
                                                self.request.method)

            if self.resource_path is None:
                self.set_status(httplib.NOT_FOUND)
                self.finish()
            else:
                filters = get_filters_args(self.request.query_arguments,
                                           self.schema, self.resource_path)
                if self.request.method != \
                        REQUEST_TYPE_READ and len(filters) > 0:
                    raise ParameterNotAllowed("argument filter is only "
                                              "allowed in %s"
                                              % REQUEST_TYPE_READ)
                # If Match support
                match = yield self.process_if_match()
                app_log.debug("If-Match result: %s" % match)
                if not match:
                    self.finish()

            if self.request.method == REQUEST_TYPE_CREATE \
                    or self.request.method == REQUEST_TYPE_UPDATE \
                    or self.request.method == REQUEST_TYPE_PATCH:
                if int(self.request.headers['Content-Length']) \
                        > MAX_BODY_SIZE:
                    raise DataValidationFailed("Content-Length too long")

        except APIException as e:
            self.on_exception(e)
            self.finish()

        except Exception, e:
            self.on_exception(e)
            self.finish()

    @gen.coroutine
    def options(self):

        resource = self.resource_path
        while resource.next is not None:
            resource = resource.next

        allowed_methods = ', '.join(resource.get_allowed_methods(self.schema))

        self.set_header(HTTP_HEADER_ALLOW, allowed_methods)

        self.set_status(httplib.OK)
        self.finish()

    @gen.coroutine
    def get(self):
        try:
            selector = self.get_query_argument(REST_QUERY_PARAM_SELECTOR, None)

            app_log.debug("Query arguments %s" % self.request.query_arguments)

            result = yield get.get_resource(self.idl, self.resource_path,
                                            self.schema, self.request.path,
                                            selector,
                                            self.request.query_arguments,
                                            fetch_readonly=True,
                                            manager=self.ref_object.manager)

            if result is None:
                self.set_status(httplib.NOT_FOUND)
            elif self.successful_query(result):
                self.set_status(httplib.OK)
                self.set_header(HTTP_HEADER_CONTENT_TYPE,
                                HTTP_CONTENT_TYPE_JSON)
                self.write(json.dumps(result))

        except APIException as e:
            self.on_exception(e)

        except Exception as e:
            self.on_exception(e)

        self.finish()

    @gen.coroutine
    def post(self):
        try:

            if HTTP_HEADER_CONTENT_LENGTH not in self.request.headers:
                raise LengthRequired

            # get the POST body
            post_data = json.loads(self.request.body)

            # create a new ovsdb transaction
            self.txn = self.ref_object.manager.get_new_transaction()

            # post_resource performs data verficiation, prepares and
            # commits the ovsdb transaction
            result = post.post_resource(post_data, self.resource_path,
                                        self.schema, self.txn,
                                        self.idl)

            status = result.status
            resource_uri = self.request.path + "/" + result.index

            if status == INCOMPLETE:
                self.ref_object.manager.monitor_transaction(self.txn)
                # on 'incomplete' state we wait until the transaction
                # completes with either success or failure
                yield self.txn.event.wait()
                status = self.txn.status

            # complete transaction
            self.transaction_complete(status)

            # set the http header to include URI
            self.set_header(HTTP_HEADER_LOCATION, resource_uri)

        except APIException as e:
            self.on_exception(e)

        except ValueError as e:
            self.set_status(httplib.BAD_REQUEST)
            self.set_header(HTTP_HEADER_CONTENT_TYPE,
                            HTTP_CONTENT_TYPE_JSON)
            self.write(utils.to_json_error(e))

        except Exception as e:
            self.on_exception(e)

        self.finish()

    @gen.coroutine
    def put(self):
        try:

            if HTTP_HEADER_CONTENT_LENGTH not in self.request.headers:
                raise LengthRequired

            # get the PUT body
            update_data = json.loads(self.request.body)
            # create a new ovsdb transaction
            self.txn = self.ref_object.manager.get_new_transaction()

            # put_resource performs data verfication, prepares and
            # commits the ovsdb transaction
            result = put.put_resource(update_data, self.resource_path,
                                      self.schema, self.txn, self.idl)

            status = result.status
            if status == INCOMPLETE:
                self.ref_object.manager.monitor_transaction(self.txn)
                # on 'incomplete' state we wait until the transaction
                # completes with either success or failure
                yield self.txn.event.wait()
                status = self.txn.status

            # complete transaction
            self.transaction_complete(status)

        except APIException as e:
            self.on_exception(e)

        except ValueError as e:
            self.set_status(httplib.BAD_REQUEST)
            self.set_header(HTTP_HEADER_CONTENT_TYPE,
                            HTTP_CONTENT_TYPE_JSON)
            self.write(utils.to_json_error(e))

        except Exception as e:
            self.on_exception(e)

        self.finish()

    @gen.coroutine
    def patch(self):
        try:

            if HTTP_HEADER_CONTENT_LENGTH not in self.request.headers:
                raise LengthRequired

            # get the PATCH body
            update_data = json.loads(self.request.body)
            # create a new ovsdb transaction
            self.txn = self.ref_object.manager.get_new_transaction()

            # patch_resource performs data verification, prepares and
            # commits the ovsdb transaction
            result = yield patch.patch_resource(update_data,
                                                self.resource_path,
                                                self.schema, self.txn,
                                                self.idl, self.request.path)

            status = result.status
            if status == INCOMPLETE:
                self.ref_object.manager.monitor_transaction(self.txn)
                # on 'incomplete' state we wait until the transaction
                # completes with either success or failure
                yield self.txn.event.wait()
                status = self.txn.status

            # complete transaction
            self.transaction_complete(status)

        except APIException as e:
            app_log.debug("PATCH APIException")
            self.on_exception(e)

        except ValueError as e:
            self.set_status(httplib.BAD_REQUEST)
            self.set_header(HTTP_HEADER_CONTENT_TYPE,
                            HTTP_CONTENT_TYPE_JSON)
            self.write(utils.to_json_error(e))

        except Exception as e:
            app_log.debug("PATCH General Exception")
            self.on_exception(e)

        self.finish()

    @gen.coroutine
    def delete(self):

        try:
            self.txn = self.ref_object.manager.get_new_transaction()

            result = delete.delete_resource(self.resource_path,
                                            self.schema, self.txn,
                                            self.idl)
            status = result.status
            if status == INCOMPLETE:
                self.ref_object.manager.monitor_transaction(self.txn)
                # on 'incomplete' state we wait until the transaction
                # completes with either success or failure
                yield self.txn.event.wait()
                status = self.txn.status

            # complete transaction
            self.transaction_complete(status)

        except APIException as e:
            self.on_exception(e)

        except Exception as e:
            self.on_exception(e)

        self.finish()

    def transaction_complete(self, status):

        # TODO: The http status codes are currently
        # not in accordance with REST good practices.

        app_log.debug("Transaction result: %s", status)

        method = self.request.method
        if status == SUCCESS:
            if method == REQUEST_TYPE_CREATE:
                self.set_status(httplib.CREATED)
            elif method == REQUEST_TYPE_UPDATE:
                self.set_status(httplib.OK)
            elif method == REQUEST_TYPE_DELETE:
                self.set_status(httplib.NO_CONTENT)
            elif method == REQUEST_TYPE_PATCH:
                # TODO Change this to OK if the
                # PATCH response ever contains
                # data, as per RFC 5789
                self.set_status(httplib.NO_CONTENT)

        elif status == UNCHANGED:
            if method == REQUEST_TYPE_PATCH:
                # PATCH can contain a single Test operation
                # which doesn't modify the resource, per RFC
                # 5789 PATCH's status code is NO_CONTENT if
                # no message body is present
                self.set_status(httplib.NO_CONTENT)
            else:
                self.set_status(httplib.OK)

        else:
            error = self.txn.get_error()
            raise APIException(error)

    def successful_query(self, result):

        if isinstance(result, dict) and ERROR in result:
            self.set_status(httplib.BAD_REQUEST)
            self.set_header(HTTP_HEADER_CONTENT_TYPE, HTTP_CONTENT_TYPE_JSON)
            self.write(utils.to_json(result))
            return False
        else:
            return True
