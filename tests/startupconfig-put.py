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
from pprint import pprint

'''
Test script to save a new startup configuration data into OVSDB.

json.data is a file containing the tables that are to be saved to DB.
'''


with open('json.data') as data_file:
        _data = json.loads(data_file.read())
http = httplib2.Http()

_headers = {"Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/plain"}
url = 'https://172.17.0.39/rest/v1/system/full-configuration?type=startup'

_headers = {"Content-type": "multipart/form-data", "Accept": "text/plain"}
response, content = http.request(url, 'PUT', headers=_headers,
                                 body=json.dumps(_data))
print(response)
print(content)
