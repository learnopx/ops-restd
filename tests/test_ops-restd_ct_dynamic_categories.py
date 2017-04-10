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

from opsvsi.docker import *
from opsvsi.opsvsitest import *

import json
import httplib

from opsvsiutils.restutils.utils import execute_request, login, \
    get_switch_ip, rest_sanity_check, get_container_id, get_json, \
    get_server_crt, remove_server_crt
from copy import deepcopy

NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0

STATIC_PREFIX = "192.168.1.0/16"
CONNECTED_PREFIX = "192.168.2.0/16"
HTML_SLASH = "%2F"

CONFIG = "configuration"
STATUS = "status"

FROM_STATIC = "static"
FROM_CONNECTED = "connected"

base_route_data = {
    "configuration": {
        "address_family": "ipv4",
        "distance": 1,
        "from": "%(from)",
        "metric": 0,
        "prefix": "%(prefix)",
        "sub_address_family": "unicast"
    }
}

insert_route = (
    '["OpenSwitch",{'
    '"op": "insert",'
    '"table": "Route",'
    '"row": {'
    '"address_family": "ipv4",'
    '"distance": 1,'
    '"from": "%(from)s",'
    '"metric": 0,'
    '"prefix": "%(prefix)s",'
    '"sub_address_family": "unicast",'
    '"vrf": ["uuid","%(vrf)s"]'
    '} '
    '}]'
    )

ovsdb_client_transact = "ovsdb-client transact '%s'"


class myTopo(Topo):
    def build(self, hsts=0, sws=1, **_opts):
        self.hsts = hsts
        self.sws = sws
        self.switch = self.addSwitch("s1")


@pytest.fixture("function")
def netop_login(request):
    request.cls.test_var.cookie_header = login(request.cls.test_var.SWITCH_IP)


@pytest.fixture("function")
def create_static_route(request):
    cookie_header = request.cls.test_var.cookie_header
    path = request.cls.test_var.PATH
    switch_ip = request.cls.test_var.SWITCH_IP

    data = create_route(FROM_STATIC, STATIC_PREFIX, cookie_header,
                        path, switch_ip)

    def cleanup():
        delete_route(FROM_STATIC, STATIC_PREFIX, cookie_header,
                     path, switch_ip)

    request.addfinalizer(cleanup)

    return data


def create_route(from_type, prefix, cookie_header, path, switch_ip):
    info("\n########## Create Static Route "
         "##########\n")
    data = deepcopy(base_route_data)
    data[CONFIG]["from"] = from_type
    data[CONFIG]["prefix"] = prefix

    status_code, response_data = execute_request(
        path, "POST", json.dumps(data),
        switch_ip, xtra_header=cookie_header)

    assert status_code == httplib.CREATED, \
        "Unexpected status code. Received: %s Response data: %s " % \
        (status_code, response_data)
    info("### Static route created ###\n")

    info("\n########## End Create Static Route "
         "##########\n")
    return data


def delete_route(from_type, prefix, cookie_header, path, switch_ip):
    info("\n########## Delete Static Route "
         "##########\n")
    path = path + "/%s/" % from_type + \
        STATIC_PREFIX.replace("/", HTML_SLASH)

    status_code, response_data = execute_request(
        path, "GET", None,
        switch_ip, xtra_header=cookie_header)

    if status_code == httplib.OK:
        status_code, response_data = execute_request(
            path, "DELETE", None,
            switch_ip, xtra_header=cookie_header)
        assert status_code == httplib.NO_CONTENT, \
            "Unexpected status code. Received: %s Response data: %s " % \
            (status_code, response_data)
    else:
        info("Route doesn't exist")

    info("\n########## End Delete Static Route "
         "##########\n")


def get_vrf_uuid(switch, vrf_name):
    cmd_ovsctl = '/usr/bin/ovs-vsctl get VRF ' + vrf_name + ' _uuid'
    return switch.cmd(cmd_ovsctl).rstrip("\r\n")


class DynamicCategoryTest (OpsVsiTest):
    def setupNet(self):
        self.net = Mininet(topo=myTopo(hsts=NUM_HOSTS_PER_SWITCH,
                                       sws=NUM_OF_SWITCHES,
                                       hopts=self.getHostOpts(),
                                       sopts=self.getSwitchOpts()),
                           switch=VsiOpenSwitch, host=None, link=None,
                           controller=None, build=True)

        self.SWITCH_IP = get_switch_ip(self.net.switches[0])
        self.PATH = "/rest/v1/system/vrfs/vrf_default/routes"
        self.cookie_header = None

    def post_static_route(self, data):
        info("\n########## Test to Create Static Route "
             "##########\n")
        # Verify data
        new_path = self.PATH + "/%s/" % FROM_STATIC \
            + STATIC_PREFIX.replace("/", HTML_SLASH)
        status_code, response_data = execute_request(
            new_path, "GET", None, self.SWITCH_IP,
            xtra_header=self.cookie_header)

        assert status_code == httplib.OK, "Failed to query route"
        json_data = get_json(response_data)

        assert json_data[CONFIG] == data[CONFIG], \
            "Configuration data is not equal that posted data"
        info("### Configuration data validated ###\n")

        info("\n########## End Test to Create Static Route "
             "##########\n")

    def post_static_route_remove_from_field(self):
        info("\n########## Test to Create Static Route "
             "without 'from' field ##########\n")
        data = deepcopy(base_route_data)
        data[CONFIG].pop("from")
        data[CONFIG]["prefix"] = STATIC_PREFIX
        status_code, response_data = execute_request(
            self.PATH, "POST", json.dumps(data),
            self.SWITCH_IP, xtra_header=self.cookie_header)

        assert status_code == httplib.BAD_REQUEST, \
            "Unexpected status code. Received: %s Response data: %s " % \
            (status_code, response_data)

        info("\n########## End Test to Create Static Route "
             "without 'from' field ##########\n")

    def post_connected_route(self):
        info("\n########## Test Create Connected Route ##########\n")
        data = deepcopy(base_route_data)
        data[CONFIG]["from"] = "connected"
        data[CONFIG]["prefix"] = CONNECTED_PREFIX
        status_code, response_data = execute_request(
            self.PATH, "POST", json.dumps(data),
            self.SWITCH_IP, xtra_header=self.cookie_header)

        assert status_code == httplib.METHOD_NOT_ALLOWED, \
            "Unexpected status code. Received: %s Response data: %s " % \
            (status_code, response_data)
        info("### Route cannot be created  ###\n")

        info("\n########## End Test Create Connected Route ##########\n")

    def verify_connected_route_categories(self):
        info("\n########## Test Verify Connected Route Categories "
             "##########\n")
        s1 = self.net.switches[0]
        # Get vrf_default uuid
        vrf_default_uuid = get_vrf_uuid(s1, "vrf_default")
        # Set other data
        from_type = "connected"
        # Set transaction data
        transact_data = \
            insert_route % {"prefix": CONNECTED_PREFIX,
                            "vrf": vrf_default_uuid,
                            "from": from_type}
        cmd_transact = ovsdb_client_transact % transact_data
        info("Transaction: %s \n" % cmd_transact)
        info(cmd_transact + "\n")
        # Execute transaction
        output = s1.cmd(cmd_transact)
        output = output.rstrip("\r\n")
        info("Response output: %s \n" % output)

        # Verify data
        new_path = self.PATH + "/" + from_type + "/" \
            + CONNECTED_PREFIX.replace("/", HTML_SLASH)

        status_code, response_data = execute_request(
            new_path, "GET", None, self.SWITCH_IP,
            xtra_header=self.cookie_header)

        assert status_code == httplib.OK, "Failed to query route"
        json_data = get_json(response_data)
        info("Response data: %s \n " % json_data)

        # Verify if the follows columns are categorized as status
        assert "prefix" in json_data[STATUS]
        assert "address_family" in json_data[STATUS]
        assert "sub_address_family" in json_data[STATUS]
        assert "metric" in json_data[STATUS]

        info("\n########## End Test Verify Connected Route Categories "
             "##########\n")


class Test_DynamicCategory:
    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_class(cls):
        Test_DynamicCategory.test_var = DynamicCategoryTest()
        get_server_crt(cls.test_var.net.switches[0])
        rest_sanity_check(cls.test_var.SWITCH_IP)
        cls.container_id = get_container_id(cls.test_var.net.switches[0])

    def teardown_class(cls):
        Test_DynamicCategory.test_var.net.stop()
        remove_server_crt()

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def __del__(self):
        del self.test_var

    def test_call_post_static_route(self, netop_login, create_static_route):
        data = create_static_route
        self.test_var.post_static_route(data)

    def test_call_post_static_route_remove_from_field(self, netop_login):
        self.test_var.post_static_route_remove_from_field()

    def test_call_post_connected_route(self, netop_login):
        self.test_var.post_connected_route()

    def test_call_verify_connected_route_categories(self, netop_login):
        self.test_var.verify_connected_route_categories()
