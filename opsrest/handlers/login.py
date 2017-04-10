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
from tornado.web import MissingArgumentError
import re
import httplib
import userauth

from opsrest.handlers import base
from opsrest.exceptions import APIException, AuthenticationFailed,\
    DataValidationFailed
from opsrest.constants import USERNAME_KEY
from opsrest.utils.userutils import check_user_login_authorization
from opsrest.utils.utils import redirect_http_to_https


class LoginHandler(base.BaseHandler):

    # pass the application reference to the handlers
    def initialize(self, ref_object):
        self.error_message = None

    # Overwrite BaseHandler's prepare, as LoginHandler does not
    # require authentication check prior to other operations
    def prepare(self):
        try:
            redirect_http_to_https(self)

        except Exception as e:
            self.on_exception(e)

    @gen.coroutine
    def get(self):
        try:
            app_log.debug("Executing Login GET...")

            is_authenticated = userauth.is_user_authenticated(self)
            if not is_authenticated:
                raise AuthenticationFailed
            else:
                self.set_status(httplib.OK)

        except APIException as e:
            self.on_exception(e)

        except Exception as e:
            self.on_exception(e)

        self.finish()

    @gen.coroutine
    def post(self):
        try:
            app_log.debug("Executing Login POST...")

            username = self.get_argument(USERNAME_KEY)

            check_user_login_authorization(username)

            login_success = userauth.handle_user_login(self)
            if not login_success:
                raise AuthenticationFailed('invalid username/password '
                                           'combination')
            else:
                self.set_status(httplib.OK)

        except MissingArgumentError as e:
            self.on_exception(DataValidationFailed('Missing username or '
                                                   'password'))

        except APIException as e:
            self.on_exception(e)

        except Exception as e:
            self.on_exception(e)

        self.finish()
