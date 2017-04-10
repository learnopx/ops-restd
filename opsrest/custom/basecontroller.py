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

from opsrest.constants import\
    REST_VERSION_PATH, OVSDB_SCHEMA_SYSTEM_URI, OVSDB_SCHEMA_CONFIG
from opsrest.exceptions import MethodNotAllowed, NotFound
from opsrest.patch import create_patch, apply_patch
from tornado import gen


class BaseController():
    """
    BaseController base controller class with generic
    CRUD operations.
    """

    def __init__(self, context=None):
        self.base_uri_path = ""
        self.context = context
        self.initialize()

    def initialize(self):
        pass

    @gen.coroutine
    def create(self, data, current_user=None, query_args=None):
        raise MethodNotAllowed

    @gen.coroutine
    def update(self, item_id, data, current_user=None, query_args=None):
        raise MethodNotAllowed

    @gen.coroutine
    def delete(self, item_id, current_user=None, query_args=None):
        raise MethodNotAllowed

    @gen.coroutine
    def get(self, item_id, current_user=None, selector=None, query_args=None):
        raise MethodNotAllowed

    @gen.coroutine
    def get_all(self, current_user=None, selector=None, query_args=None):
        raise MethodNotAllowed

    @gen.coroutine
    def create_uri(self, item_id):
        return REST_VERSION_PATH + OVSDB_SCHEMA_SYSTEM_URI + "/" +\
            self.base_uri_path + "/" + item_id

    @gen.coroutine
    def get_patch(self, item_id=None, current_user=None, selector=None,
                  query_args=None):
        result = yield self.get(item_id, current_user, selector, query_args)
        raise gen.Return(result)

    @gen.coroutine
    def patch(self, item_id, data, current_user=None, query_args=None):
        try:
            # Get the resource's JSON to patch
            resource_json = yield self.get_patch(item_id, current_user,
                                                 OVSDB_SCHEMA_CONFIG,
                                                 query_args)

            if resource_json is None:
                raise NotFound

            # Create and verify patch
            (patch, needs_update) = create_patch(data)

            # Apply patch to the resource's JSON
            patched_resource = apply_patch(patch, resource_json)

            # Update resource only if needed, since a valid
            # patch can contain PATCH_OP_TEST operations
            # only, which do not modify the resource
            if needs_update:
                yield self.update(item_id, patched_resource, current_user, query_args)

        # In case the resource doesn't implement GET/PUT
        except MethodNotAllowed:
            raise MethodNotAllowed("PATCH not allowed on resource")
