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

import os
import sys
import time
import pytest
import subprocess
import shutil

from opsvsi.docker import *
from opsvsi.opsvsitest import *
from opsvsiutils.systemutil import *

'''
This script copies user config files(config_test1.db, config_test2.db,
empty_config.db) and runconfig_test_in_docker.py onto the switch. The
runconfig_test_in_docker.py verifies if the user config is written
successfully to the OVSDB.
'''

NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0


class myTopo(Topo):
    def build(self, hsts=0, sws=1, **_opts):

        self.hsts = hsts
        self.sws = sws
        switch = self.addSwitch("s1")


class configTest (OpsVsiTest):
    def setupNet(self):
        self.net = Mininet(topo=myTopo(hsts=NUM_HOSTS_PER_SWITCH,
                                       sws=NUM_OF_SWITCHES,
                                       hopts=self.getHostOpts(),
                                       sopts=self.getSwitchOpts()),
                           switch=VsiOpenSwitch,
                           host=Host,
                           link=OpsVsiLink,
                           controller=None,
                           build=True)

    def copy_to_docker(self):
        info("\n########## Copying required files to docker ##########\n")
        src_path = os.path.dirname(os.path.realpath(__file__))
        switch = self.net.switches[0]
        testid = switch.testid
        script_shared_local = '/tmp/openswitch-test/' + testid + '/' + \
                              switch.name + \
                              '/shared/runconfig_test_in_docker.py'
        script_shared_local_runconfig = '/tmp/openswitch-test/' + testid + \
                                        '/' + switch.name + \
                                        '/shared/runconfig.py'
        script_shared_test_file1 = '/tmp/openswitch-test/' + testid + '/' + \
                                   switch.name + '/shared' + '/config_test1'
        script_shared_test_file2 = '/tmp/openswitch-test/' + testid + '/' + \
                                   switch.name + '/shared' + '/config_test2'
        script_shared_test_file3 = '/tmp/openswitch-test/' + testid + '/' + \
                                   switch.name + '/shared' + '/empty_config.db'

        shutil.copy2(os.path.join(src_path, "runconfig_test_in_docker.py"),
                     script_shared_local)
        shutil.copy2(os.path.join(src_path, "config_test1.db"),
                     script_shared_test_file1)
        shutil.copy2(os.path.join(src_path, "config_test2.db"),
                     script_shared_test_file2)
        shutil.copy2(os.path.join(src_path, "empty_config.db"),
                     script_shared_test_file3)

    def verify_runconfig(self):
        info('########################################################\n')
        info('###### Testing full config and empty config   ######\n')
        info('########################################################\n')
        switch = self.net.switches[0]
        script_shared_docker = '/shared/runconfig_test_in_docker.py'
        out = switch.cmd('python ' + script_shared_docker)
        res = out.find("Test Failure")
        assert res == -1, "\n### Write was not successful ###\n"
        info("\n### Write was successful ###\n")

@pytest.mark.skipif(True,reason="Disabling until this test is fixed for the current schema")
class Test_config:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_class(cls):
        Test_config.test_var = configTest()

    def teardown_class(cls):
        Test_config.test_var.net.stop()

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def __del__(self):
        del self.test_var

    def test_run(self):
        self.test_var.copy_to_docker()
        self.test_var.verify_runconfig()
