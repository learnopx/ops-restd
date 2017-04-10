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

import os.path
import custom

from tornado.options import define

define("HTTPS", default=False, help="turn on serving HTTPS")
define("HTTPS_port", default=443, help="run on the given port", type=int)
define("HTTP_port", default=8091, help="run on the given port", type=int)
define("listen", default="localhost", help="listen only on the specified address")
define("config", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")
define("create_ssl", default=False, help="create SSL certificate if needed")
define("force_https", default=False,
       help="causes all HTTP connections to be redirected to HTTPS")

settings = {}
settings['logging'] = 'info'
settings["static_path"] = os.path.join(os.path.dirname(__file__), "static")
settings["template_path"] = os.path.join(os.path.dirname(__file__),
                                         "templates")
settings['ovs_remote'] = 'unix:/var/run/openvswitch/db.sock'
settings['ovs_schema'] = '/usr/share/openvswitch/vswitch.ovsschema'
settings['ext_schema'] = '/usr/share/openvswitch/openswitch.opsschema'
settings['auth_enabled'] = True
settings['cfg_db_schema'] = '/usr/share/openvswitch/configdb.ovsschema'

settings["account_schema"] = os.path.join(os.path.dirname(custom.__file__),
                                          'schemas/Account.json')
settings["passwd_srv_yaml"] = '/etc/ops-passwd-srv/ops-passwd-srv.yaml'
