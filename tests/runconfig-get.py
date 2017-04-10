# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
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

# NOTE: run using Python3
import urllib
import httplib2
import json

'''
Test script to GET running configuration of OVSDB.
'''
http = httplib2.Http()

_headers = {"Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/plain"}
# GET to fetch system info from the DB
url = 'https://172.17.0.39/rest/v1/system/full-configuration?type=running'
response, content = http.request(url, 'GET', headers=_headers)
print(response)
print(content)
