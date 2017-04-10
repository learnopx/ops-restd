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

import json

from tornado.log import app_log


# This function is used to convert the response from string to list of json
# objects
def convert_string_to_json(data, _w=json.decoder.WHITESPACE.match):
        decoder = json.JSONDecoder()
        objs = []
        str_len = len(data)
        offset = 0
        while offset != str_len:
            # get offset where the json object begins
            str_offset = _w(data, offset).end()
            # retrieve the json object
            obj, offset = decoder.raw_decode(data, idx=str_offset)
            # change the offset to the next json object
            offset = _w(data, offset).end()
            # Add the obj to the list
            objs.append(obj)
        return objs
