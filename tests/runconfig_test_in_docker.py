#!/usr/bin/env python
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from opsrest.settings import settings
from opsrest.manager import OvsdbConnectionManager
from opsrest.utils import utils
from opsrest import resource
from opslib import restparser
import ovs
import json
import sys
import time
import traceback
sys.path.insert(0, '/usr/lib/python2.7/site-packages/runconfig')
import runconfig

CONFIG_FILENAME_1 = "/shared/config_test1"
CONFIG_FILENAME_2 = "/shared/config_test2"
CONFIG_FILENAME_3 = "/shared/empty_config.db"


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def test_read():

    manager = OvsdbConnectionManager(settings.get('ovs_remote'),
                                     settings.get('ovs_schema'))
    manager.start()
    idl = manager.idl

    init_seq_no = 0
    # Wait until the connection is ready
    while True:
        idl.run()
        # Print self.idl.change_seqno
        if init_seq_no != idl.change_seqno:
            break
        time.sleep(0.001)

    schema = restparser.parseSchema(settings.get('ext_schema'))

    run_config_util = runconfig.RunConfigUtil(idl, schema)
    config = run_config_util.get_config()
    '''
    TODO: Adding json.dumps and the json.loads as a workaround because
    the config returned from test_read has a missing unicode character
    for keys
    '''
    temp_config = json.dumps(config)
    config = json.loads(temp_config)
    filename = 'config.db'
    with open(filename, 'w') as fp:
        json.dump(config, fp, sort_keys=True, indent=4,
                  separators=(',', ': '))
        fp.write('\n')
    return config


def test_write(filename):

    with open(filename) as json_data:
        data = json.load(json_data)
        json_data.close()

    # Set up IDL
    manager = OvsdbConnectionManager(settings.get('ovs_remote'),
                                     settings.get('ovs_schema'))
    manager.start()
    manager.idl.run()

    init_seq_no = 0
    while True:
        manager.idl.run()
        if init_seq_no != manager.idl.change_seqno:
            break

    # Read the schema
    schema = restparser.parseSchema(settings.get('ext_schema'))
    run_config_util = runconfig.RunConfigUtil(manager.idl, schema)
    run_config_util.write_config_to_db(data)


# Empty config test case
def test_empty_config(full_config, empty_config):

    with open(empty_config) as json_data:
        empty_config_to_write = json.load(json_data)
        json_data.close()

    test_write(empty_config)
    config1 = test_read()

    test_write(full_config)
    test_write(empty_config)
    config2 = test_read()

    res = ordered(config2) == ordered(config1)
    return res


# Read and modify
def test_write_read_compare(fname):

    with open(fname) as json_data:
        config_to_write = json.load(json_data)
        json_data.close()

    test_write(fname)

    config = test_read()

    res = ordered(config_to_write) == ordered(config)

    return res


if __name__ == "__main__":
    result = test_write_read_compare(CONFIG_FILENAME_1)
    if result:
        result = test_write_read_compare(CONFIG_FILENAME_2)
        if result:
            # Commenting out the empty test case until restrictions on deletion
            # are enforced from schema (eg. for VLAN table).
            #result = test_empty_config(CONFIG_FILENAME_2, CONFIG_FILENAME_3)
            pass
        else:
            print "Test Failure"
    else:
        print "Test Failure"
