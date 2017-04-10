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

# Third party imports
import yaml

from tornado.log import app_log

# Local imports
from opsrest.settings import settings
from opsrest.constants import (PASSWD_SRV_SOCK_TYPE_KEY,
                               PASSWD_SRV_PUB_TYPE_KEY)


class PasswordServerConfig(object):
    __instance = None

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(PasswordServerConfig, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.sock_fd = ''
        self.pub_key_loc = ''
        self.__get_passwd_srv_files_location__()

    def __get_passwd_srv_files_location__(self):
        try:
            passwd_srv_yaml = \
                open(settings['passwd_srv_yaml'], "r")
            passwd_srv_files = yaml.load_all(passwd_srv_yaml)
            for file in passwd_srv_files:
                for k, v in file.items():
                    passwd_srv_list = v
            for element in passwd_srv_list:
                if element['type'] == PASSWD_SRV_SOCK_TYPE_KEY:
                    self.sock_fd = element['path']
                if element['type'] == PASSWD_SRV_PUB_TYPE_KEY:
                    self.pub_key_loc = element['path']
            passwd_srv_yaml.close()
        except IOError as e:
            app_log.debug("Failed to open Password Server YAML file: %s" % e)
