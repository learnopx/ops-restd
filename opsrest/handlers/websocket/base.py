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

import uuid
import userauth
from tornado import websocket
from tornado.log import app_log
from opsrest.utils.utils import redirect_http_to_https
from opsrest.utils.userutils import (
    check_authenticated,
    check_method_permission
)
from opsrest.constants import (
    HTTP_HEADER_CONTENT_TYPE,
    HTTP_CONTENT_TYPE_JSON,
    HTTP_HEADER_LINK,
    REST_LOGIN_PATH,
    REQUEST_TYPE_READ
)
from opsrest.exceptions import NotAuthenticated, AuthenticationFailed


class WSBaseHandler(websocket.WebSocketHandler):
    websockets = {}

    def initialize(self, ref_object):
        self.ref_object = ref_object
        self.manager = self.ref_object.manager
        self.schema = self.ref_object.restschema
        self.idl = self.manager.idl
        self.id = self.generate_id()

    def prepare(self):
        try:
            redirect_http_to_https(self)

            request_type = REQUEST_TYPE_READ
            check_authenticated(self, request_type)
            check_method_permission(self, request_type)
        except Exception as e:
            self.error_message = str(e)

            if isinstance(e, NotAuthenticated) or \
               isinstance(e, AuthenticationFailed):
                app_log.error("Caught Authentication Exception: %s" % e)
                self.set_header(HTTP_HEADER_LINK, REST_LOGIN_PATH)

            self.set_status(e.status_code)
            self.set_header(HTTP_HEADER_CONTENT_TYPE, HTTP_CONTENT_TYPE_JSON)
            self.write(self.error_message)
            self.finish()

    def _open(self):
        pass

    def _on_close(self):
        pass

    def check_origin(self, origin):
        return True

    def open(self):
        app_log.debug("WebSocket event: OPENED")
        app_log.debug("WebSocket ID: %s" % self.id)
        WSBaseHandler.websockets[self.id] = self

        self._open()

    def on_close(self):
        app_log.debug("WebSocket event: CLOSED")

        if self.id in WSBaseHandler.websockets:
            del WSBaseHandler.websockets[self.id]

        self._on_close()

    def on_message(self, msg):
        app_log.debug("WebSocket event: MESSAGE RECEIVED")
        app_log.debug("Message: %s" % msg)

        # No processing at the moment.

    def send_message(self, msg):
        self.write_message(msg)
        app_log.debug("WebSocket event: MESSAGE SENT")
        app_log.debug("Message: %s" % msg)

    @staticmethod
    def get_websocket(id):
        ws = None
        if id in WSBaseHandler.websockets:
            ws = WSBaseHandler.websockets[id]

        return ws

    def generate_id(self):
        while True:
            new_id = str(uuid.uuid4())
            if new_id not in WSBaseHandler.websockets:
                break

        return new_id

    def get_current_user(self):
        return userauth.get_request_user(self)
