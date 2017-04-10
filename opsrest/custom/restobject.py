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

# Local imports
from opsrest.constants import \
    OVSDB_SCHEMA_CONFIG, \
    OVSDB_SCHEMA_STATUS, \
    OVSDB_SCHEMA_STATS


class RestObject(object):
    def __init__(self):
        pass

    def to_json(self):
        json_dict = self.__dict__
        collections = tuple, list, set, frozenset, dict
        result = {}
        for key, value in json_dict.items():
            if isinstance(value, RestObject):
                result[key] = value.to_json()
            elif isinstance(value, collections):
                result[key] = type(value)(collection_value.to_json()
                                          if isinstance(collection_value,
                                                        RestObject)
                                          else collection_value
                                          for collection_value in value)
            else:
                result[key] = value
        return result

    @staticmethod
    def from_json(dict_data):
        instance = RestObject()
        collections = tuple, list, set, frozenset
        for key, value in dict_data.items():
            if isinstance(value, dict):
                # A dict is a new object
                if value:
                    setattr(instance, key, RestObject.from_json(value))
                else:
                    setattr(instance, key, value)
            elif isinstance(value, collections):
                # A list may have an object inside
                setattr(instance, key,
                        type(value)(RestObject.from_json(collection_value)
                                    if isinstance(collection_value, dict)
                                    else collection_value
                                    for collection_value in value))
            else:
                setattr(instance, key, value)
        return instance

    @staticmethod
    def to_json_list(obj_list):
        dict_list = []
        for obj_data in obj_list:
            dict_list.append(obj_data.to_json())
        return dict_list

    @staticmethod
    def create_empty_json(selector=None):
        empty_json = {}
        if selector == OVSDB_SCHEMA_CONFIG:
            empty_json[OVSDB_SCHEMA_CONFIG] = {}
        elif selector == OVSDB_SCHEMA_STATUS:
            empty_json[OVSDB_SCHEMA_STATUS] = {}
        elif selector == OVSDB_SCHEMA_STATS:
            empty_json[OVSDB_SCHEMA_STATS] = {}
        else:
            empty_json = {OVSDB_SCHEMA_CONFIG: {},
                          OVSDB_SCHEMA_STATUS: {},
                          OVSDB_SCHEMA_STATS: {}}
        return empty_json
