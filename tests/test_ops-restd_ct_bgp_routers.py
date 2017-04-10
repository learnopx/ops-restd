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
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, See the
# License for the specific language governing permissions and limitations
# under the License.


import pytest

from opsvsi.docker import *
from opsvsi.opsvsitest import *
from opsvsiutils.restutils.utils import execute_request, get_switch_ip, \
    get_json, rest_sanity_check, login
import json
import httplib
import urllib
import os
import sys
import time
import subprocess
import shutil
import socket
import copy

NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0
_DATA = {"configuration": {"asn": 6004, "router_id": "10.10.0.4",
         "deterministic_med": False, "always_compare_med": False,
         "networks": ["10.0.0.10/16", "10.1.2.10/24"],
         "gr_stale_timer": 1, "maximum_paths": 1,
         "fast_external_failover": False, "log_neighbor_changes": False}}

_DATA_COPY = copy.deepcopy(_DATA)
del _DATA_COPY['configuration']['asn']


@pytest.fixture
def netop_login(request):
    request.cls.test_var.cookie_header = login(request.cls.test_var.SWITCH_IP)


class myTopo(Topo):
    def build(self, hsts=0, sws=1, **_opts):
        self.hsts = hsts
        self.sws = sws
        switch = self.addSwitch("s1")


class QueryBGPRoutersTest (OpsVsiTest):

    def setupNet(self):
        host_opts = self.getHostOpts()
        switch_opts = self.getSwitchOpts()
        ecmp_topo = myTopo(hsts=NUM_HOSTS_PER_SWITCH, sw=NUM_OF_SWITCHES,
                           hopts=host_opts, sopts=switch_opts)
        self.net = Mininet(ecmp_topo, switch=VsiOpenSwitch, host=Host,
                           link=OpsVsiLink, controller=None, build=True)
        self.SWITCH_IP = get_switch_ip(self.net.switches[0])

        self.path_bgp = '/rest/v1/system/vrfs/vrf_default/bgp_routers'
        self.path_id = '/rest/v1/system/vrfs/vrf_default/bgp_routers/6004'
        self.cookie_header = None

    def post_setup(self, cookie_header=None):
        if cookie_header is None:
            cookie_header = login(self.SWITCH_IP)
        status_code, response_data = execute_request(
            self.path_bgp, "POST", json.dumps(_DATA),
            self.SWITCH_IP, False, xtra_header=cookie_header)
        assert status_code == httplib.CREATED, ("Wrong status code %s " %
                                                status_code)

    def delete_teardown(self, cookie_header=None):
        if cookie_header is None:
            cookie_header = login(self.SWITCH_IP)
        status_code, response_data = execute_request(
            self.path_id, "DELETE", None,
            self.SWITCH_IP, False, xtra_header=cookie_header)
        assert (status_code == httplib.NO_CONTENT or
                status_code == httplib.NOT_FOUND), ("Wrong status code %s " %
                                                    status_code)

    def verify_get_bgp_routers(self):
        info("\n#####################################################\n")
        info("#         Testing GET for BGP_Routers               #")
        info("\n#####################################################\n")

        status_code, response_data = execute_request(
            self.path_id, "GET", None,
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        status_code == httplib.OK, ("Wrong status code %s " %
                                    status_code)

        d = get_json(response_data)
        assert d['configuration'] == _DATA_COPY['configuration']

        info('GET for BGP router with asn: ' +
             str(_DATA['configuration']['asn']) + ' passed successfully')

    def verify_post_bgp_routers(self):

        info("\n#####################################################\n")
        info("#         Testing POST for BGP_Routers              #")
        info("\n#####################################################\n")

        status_code, response_data = execute_request(
            self.path_bgp, "POST", json.dumps(_DATA),
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        assert status_code == httplib.CREATED, ("Wrong status code %s " %
                                                status_code)

        status_code, response_data = execute_request(
            self.path_id, "GET", None,
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        assert status_code == httplib.OK, ("Wrong status code %s " %
                                           status_code)

        d = get_json(response_data)
        assert d['configuration'] == _DATA_COPY['configuration']
        info('Successful')

    def verify_put_bgp_routers(self):

        info("\n#####################################################\n")
        info("#         Testing PUT for BGP_Routers               #")
        info("\n#####################################################\n")

        _DATA_COPY['configuration']['networks'] = ["10.10.1.0/24"]
        status_code, response_data = execute_request(
            self.path_id, "PUT", json.dumps(_DATA_COPY),
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        assert status_code == httplib.OK, ("Wrong status code %s " %
                                           status_code)

        status_code, response_data = execute_request(
            self.path_id, "GET", None,
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        status_code == httplib.OK, ("Wrong status code %s " %
                                    status_code)

        content = response_data
        d = get_json(content)
        assert d['configuration'] == _DATA_COPY['configuration']
        info('Successful')

    def verify_delete_bgp_routers(self):

        info("\n#####################################################\n")
        info("#         Testing DELETE for BGP_Routers            #")
        info("\n#####################################################\n")

        # DELETE the bgp_router
        status_code, response_data = execute_request(
            self.path_id, "DELETE", None,
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        assert status_code == httplib.NO_CONTENT, ("Wrong status code %s " %
                                                   status_code)

        # GET after deleting the bgp_router
        status_code, response_data = execute_request(
            self.path_id, "GET", None,
            self.SWITCH_IP, False, xtra_header=self.cookie_header)
        assert status_code == httplib.NOT_FOUND, ("Wrong status code %s " %
                                                  status_code)
        info('Successful\n')


@pytest.mark.skipif(True, reason="Disabling since test case already ported.")
class Test_bgp_routers:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_class(cls):
        Test_bgp_routers.test_var = QueryBGPRoutersTest()
        rest_sanity_check(cls.test_var.SWITCH_IP)

    def teardown_class(cls):
        Test_bgp_routers.test_var.net.stop()

    def setup_method(self, method):
        self.test_var.post_setup()

    def teardown_method(self, method):
        self.test_var.delete_teardown()

    def __def__(self):
        del self.test_var

    def test_get(self, netop_login):
        self.test_var.verify_get_bgp_routers()

    def test_post(self, netop_login):
        self.test_var.verify_post_bgp_routers()

    def test_put(self, netop_login):
        self.test_var.verify_put_bgp_routers()

    def test_delete(self, netop_login):
        self.test_var.verify_delete_bgp_routers()
