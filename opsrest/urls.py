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

from opsrest.handlers.staticcontent import StaticContentHandler
from opsrest.handlers.login import LoginHandler
from opsrest.handlers.logout import LogoutHandler
from opsrest.handlers.ovsdbapi import OVSDBAPIHandler
from opsrest.handlers.customrest import CustomRESTHandler
from opsrest.handlers.websocket.notifications import WSNotificationsHandler
from custom.logcontroller import LogController
from custom.accountcontroller import AccountController
from custom.configcontroller import ConfigController

REGEX_RESOURCE_ID = '?(?P<resource_id>[A-Za-z0-9-_]+[$]?)?/?'

url_patterns =\
    [(r'/login', LoginHandler),
     # TODO new handler for login API to replace /login above
     (r'/rest/v1/login', LoginHandler),
     (r'/rest/v1/logout', LogoutHandler),
     (r'/rest/v1/ws/notifications', WSNotificationsHandler),
     (r'/rest/v1/system', OVSDBAPIHandler),
     (r'/rest/v1/system/.*', OVSDBAPIHandler)]

custom_url_patterns =\
    [(r'/rest/v1/logs', CustomRESTHandler, LogController),
     (r'/account', CustomRESTHandler, AccountController),
     # TODO new handler for account API to replace /account above
     (r'/rest/v1/account', CustomRESTHandler, AccountController),
     (r'/rest/v1/system/full-configuration', CustomRESTHandler,
      ConfigController)]

static_url_patterns =\
    [(r"/api/(.*)", StaticContentHandler,
     {"path": "/srv/www/api", "default_filename": "index.html"}),
     (r"/(.*)", StaticContentHandler,
     {"path": "/srv/www/static", "default_filename": "index.html"})]
