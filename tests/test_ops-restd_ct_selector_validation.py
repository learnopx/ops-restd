#!/usr/bin/env python
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
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

import pytest

from opsvsi.docker import *
from opsvsi.opsvsitest import *

import json
import httplib

from opsvsiutils.restutils.utils import execute_request, login, \
    get_switch_ip, rest_sanity_check, get_server_crt, remove_server_crt

NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0


class myTopo(Topo):
    """
    Default network configuration for these tests
    """
    def build(self, hsts=0, sws=1, **_opts):
        self.hsts = hsts
        self.sws = sws
        self.addSwitch("s1")


@pytest.fixture
def netop_login(request):
    request.cls.test_var.cookie_header = login(request.cls.test_var.switch_ip)


class QuerySelectorTest(OpsVsiTest):
    def setupNet(self):
        self.net = Mininet(topo=myTopo(hsts=NUM_HOSTS_PER_SWITCH,
                                       sws=NUM_OF_SWITCHES,
                                       hopts=self.getHostOpts(),
                                       sopts=self.getSwitchOpts()),
                           switch=VsiOpenSwitch,
                           host=None,
                           link=None,
                           controller=None,
                           build=True)

        self.switch_ip = get_switch_ip(self.net.switches[0])
        self.cookie_header = None
        self.path = "/rest/v1/system/interfaces?selector=%s;depth=1"

    def test_invalid_selector(self):
        path = self.path % "invalid"
        info("\n########## Test Invalid Selector ##########\n")
        info("\n########## Executing GET to '%s' ##########\n" % path)
        status_code, response_data = execute_request(
            path, "GET", None, self.switch_ip, xtra_header=self.cookie_header)

        assert status_code == httplib.BAD_REQUEST, \
            "Unexpected status code. Received: %s Response data: %s " % \
            (status_code, response_data)

        info("\n########## End Executing GET to '%s' ##########\n" % path)

    def test_valid_selector(self, selector):
        path = self.path % selector
        info("\n########## Test Valid Selector: '%s' ##########\n" % selector)
        info("\n########## Executing GET to '%s' ##########\n" % path)
        status_code, response_data = execute_request(
            path, "GET", None, self.switch_ip, xtra_header=self.cookie_header)

        assert status_code == httplib.OK, \
            "Unexpected status code. Received: %s Response data: %s " % \
            (status_code, response_data)

        data = json.loads(response_data)

        assert len(data) > 0, "Data is empty"
        for row in data:
            assert row.keys() == [selector], "Data not contains selector '%s' "\
                "or contains other selectors" % selector

        info("\n########## End Executing GET to '%s' ##########\n" % path)


class TestQuerySelector:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_class(cls):
        TestQuerySelector.test_var = QuerySelectorTest()
        get_server_crt(cls.test_var.net.switches[0])
        rest_sanity_check(cls.test_var.switch_ip)

    def teardown_class(cls):
        TestQuerySelector.test_var.net.stop()
        remove_server_crt()

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def __del__(self):
        del self.test_var

    def test_call_invalid_selector(self, netop_login):
        self.test_var.test_invalid_selector()

    def test_call_valid_selector_configuration(self, netop_login):
        self.test_var.test_valid_selector("configuration")

    def test_call_valid_selector_status(self, netop_login):
        self.test_var.test_valid_selector("status")

    def test_call_valid_selector_statistics(self, netop_login):
        self.test_var.test_valid_selector("statistics")
