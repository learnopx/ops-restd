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

import urllib
import httplib2
import json
import time
'''
A simple test script to test authentication using the 'userauth' module.
This is a 2 step test.

Step 1: POST to /login to send username/password combination to fetch
        the secret cookie.
step 2: Use the secret cookie to use authenticated session to GET /system
        information from the database.
'''


# POST to fetch cookie

print("\n############## running POST ##############\n")
http = httplib2.Http()
url = 'https://172.17.0.2/login'
body = {'username': 'oleg', 'password': 'oleg'}
headers = {"Content-type": "application/x-www-form-urlencoded",
           "Accept": "text/plain"}
response, content = http.request(url, 'POST', headers=headers,
                                 body=urllib.parse.urlencode(body))
print(response)
#print(content)

time.sleep(2)

# set the cookie header before doing a GET
headers = {'Cookie': response['set-cookie']}

# GET to fetch system info from the DB
print("\n############## running GET ##############\n")
url = 'https://172.17.0.9/rest/v1/system'
response, content = http.request(url, 'GET', headers=headers)
print(response)
#print(content)
