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

from tornado.web import StaticFileHandler
from tornado.log import app_log

import re

from opsrest.utils.utils import redirect_http_to_https


class StaticContentHandler(StaticFileHandler):

    def prepare(self):
        try:
            redirect_http_to_https(self)

        except Exception as e:
            self.on_exception(e)
