# -*- coding: utf-8 -*-

# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHoutput ANY WARRANTY; withoutput even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from pytest import fixture

from rest_utils_ct import (
    execute_request, get_switch_ip, get_server_crt, remove_server_crt,
    get_json, rest_sanity_check, login
)

import json
import http.client
import copy
from time import sleep
from os import environ
from operator import itemgetter


# Topology definition. the topology contains two back to back switches
# having four links between them.


TOPOLOGY = """
# +-------+     +-------+
# |  sw1  <----->  hs1  |
# +-------+     +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=oobmhost name="Host 1"] hs1

# Ports
[force_name=oobm] sw1:sp1

# Links
sw1:sp1 -- hs1:1
"""


_DATA = {"configuration": {
         "asn": 6004, "router_id": "10.10.0.4",
         "deterministic_med": False,
         "always_compare_med": False,
         "networks": ["10.0.0.10/16", "10.1.2.10/24"],
         "gr_stale_timer": 1, "maximum_paths": 1,
         "fast_external_failover": False,
         "log_neighbor_changes": False}}


_DATA_COPY = copy.deepcopy(_DATA)
del _DATA_COPY['configuration']['asn']


path_bgp = '/rest/v1/system/vrfs/vrf_default/bgp_routers'
path_id = '/rest/v1/system/vrfs/vrf_default/bgp_routers/6004'

SWITCH_IP = None
cookie_header = None
proxy = None


def post_setup():
    status_code, response_data = execute_request(
        path_bgp, "POST", json.dumps(_DATA),
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.CREATED


def delete_teardown():
    status_code, response_data = execute_request(
        path_id, "DELETE", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NO_CONTENT or \
        status_code == http.client.NOT_FOUND


@fixture()
def setup(request, topology):
    global cookie_header
    global SWITCH_IP
    global proxy
    sw1 = topology.get("sw1")
    assert sw1 is not None
    if SWITCH_IP is None:
        SWITCH_IP = get_switch_ip(sw1)
    proxy = environ["https_proxy"]
    environ["https_proxy"] = ""
    get_server_crt(sw1)
    if cookie_header is None:
        cookie_header = login(SWITCH_IP)
    post_setup()

    def cleanup():
        global cookie_header
        environ["https_proxy"] = proxy
        delete_teardown()
        remove_server_crt()
        cookie_header = None

    request.addfinalizer(cleanup)


@fixture(scope="module")
def sanity_check(topology):
    sleep(2)
    sw1 = topology.get("sw1")
    assert sw1 is not None
    get_server_crt(sw1)
    rest_sanity_check(SWITCH_IP)


def test_restd_ct_bgp_routers_get_bgp_routers(setup, sanity_check,
                                              topology, step):
    step("\n#####################################################\n")
    step("#           Testing GET for BGP_Routers               #")
    step("\n#####################################################\n")

    step('GET for BGP router with asn: {}'.format(
        str(_DATA['configuration']['asn'])))
    status_code, response_data = execute_request(
        path_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    d = get_json(response_data)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = _DATA_COPY['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_ct_bgp_routers_post_bgp_routers(setup, sanity_check,
                                               topology, step):
    step("\n#####################################################\n")
    step("#         Testing POST for BGP_Routers              #")
    step("\n#####################################################\n")

    status_code, response_data = execute_request(
        path_bgp, "POST", json.dumps(_DATA),
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.CREATED

    status_code, response_data = execute_request(
        path_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    d = get_json(response_data)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = _DATA_COPY['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_ct_bgp_routers_put_bgp_routers(setup, sanity_check,
                                              topology, step):
    step("\n#####################################################\n")
    step("#         Testing PUT for BGP_Routers               #")
    step("\n#####################################################\n")

    aux = copy.deepcopy(_DATA_COPY)
    aux['configuration']['networks'] = ["10.10.1.0/24"]
    status_code, response_data = execute_request(
        path_id, "PUT", json.dumps(aux),
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    status_code, response_data = execute_request(
        path_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    status_code == http.client.OK

    content = response_data
    d = get_json(content)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = aux['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_ct_bgp_routers_delete_bgp_routers(setup, sanity_check,
                                                 topology, step):
    step("\n#####################################################\n")
    step("#         Testing DELETE for BGP_Routers            #")
    step("\n#####################################################\n")

    # DELETE the bgp_router
    status_code, response_data = execute_request(
        path_id, "DELETE", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NO_CONTENT

    # GET after deleting the bgp_router
    status_code, response_data = execute_request(
        path_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NOT_FOUND
