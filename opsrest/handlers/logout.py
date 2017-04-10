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

from tornado import gen
from tornado.log import app_log
import httplib
import userauth

from opsrest.handlers import base
from opsrest.exceptions import APIException
from opsrest.utils.utils import redirect_http_to_https
from opsrest.utils.userutils import check_authenticated

class LogoutHandler(base.BaseHandler):

    # pass the application reference to the handlers
    def initialize(self, ref_object):
        self.error_message = None

    # Overwrite BaseHandler's prepare, as LogoutHandler does not
    # require evrything in Base
    def prepare(self):
        try:
            redirect_http_to_https(self)

            app_log.debug("Incoming request from %s: %s",
                          self.request.remote_ip,
                          self.request)

            check_authenticated(self, self.request.method)

        except Exception as e:
            self.on_exception(e)
            self.finish()

    @gen.coroutine
    def post(self):
        try:
            app_log.debug("Executing Logout POST...")

            userauth.handle_user_logout(self)
            self.set_status(httplib.OK)

        except APIException as e:
            self.on_exception(e)

        except Exception as e:
            self.on_exception(e)

        self.finish()
