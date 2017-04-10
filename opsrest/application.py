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

from tornado.web import Application, StaticFileHandler

from opsrest.manager import OvsdbConnectionManager
from opslib import restparser
from opsrest import constants
from opsvalidator import validator
from opsrest.notifications.handler import NotificationHandler
import cookiesecret


class OvsdbApiApplication(Application):
    def __init__(self, settings):
        self.settings = settings
        self.settings['cookie_secret'] = cookiesecret.generate_cookie_secret()
        schema = self.settings.get('ext_schema')
        self.restschema = restparser.parseSchema(schema)
        self.manager = OvsdbConnectionManager(self.settings.get('ovs_remote'),
                                              self.settings.get('ovs_schema'),
                                              self.restschema)
        self._url_patterns = self._get_url_patterns()
        Application.__init__(self, self._url_patterns, **self.settings)

        # We must block the application start until idl connection
        # and replica is ready
        self.manager.start()

        # Load all custom validators
        validator.init_plugins(constants.OPSPLUGIN_DIR)

        self.notification_handler = NotificationHandler(self.restschema,
                                                        self.manager)

    # adds 'self' to url_patterns
    def _get_url_patterns(self):
        from urls import url_patterns
        from urls import custom_url_patterns
        from urls import static_url_patterns

        modified_url_patterns = []

        for url, handler, controller_class in custom_url_patterns:
            params = {'ref_object': self, 'controller_class': controller_class}
            modified_url_patterns.append((url, handler, params))

        for url in url_patterns:
            modified_url_patterns.append(url + ({'ref_object': self},))

        modified_url_patterns.extend(static_url_patterns)

        return modified_url_patterns
