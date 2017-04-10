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


_DATA = {"configuration": {"asn": 6004, "router_id": "10.10.0.4",
                           "deterministic_med": False,
                           "always_compare_med": False,
                           "networks": ["10.0.0.10/16", "10.1.2.10/24"],
                           "gr_stale_timer": 1, "maximum_paths": 1,
                           "fast_external_failover": False,
                           "log_neighbor_changes": False}}

_DATA_BGP_NEIGHBORS = {"configuration": {
                       "ip_or_group_name": "172.17.0.3",
                       "inbound_soft_reconfiguration": False,
                       "passive": False, "allow_as_in": 1,
                       "remote_as": 6008, "weight": 0,
                       "is_peer_group": False, "local_as": 6007,
                       "advertisement_interval": 0, "shutdown": False,
                       "remove_private_as": False, "password": "",
                       "maximum_prefix_limit": 1, "description": "",
                       "update_source": '', "ttl_security_hops": 1,
                       "ebgp_multihop": False}}

_DATA_BGP_NEIGHBORS_COPY = copy.deepcopy(_DATA_BGP_NEIGHBORS)
del _DATA_BGP_NEIGHBORS_COPY['configuration']['ip_or_group_name']

path_bgp = '/rest/v1/system/vrfs/vrf_default/bgp_routers'
path_id = '/rest/v1/system/vrfs/vrf_default/bgp_routers/6004'
path_bgp_neighbors = ('/rest/v1/system/vrfs/vrf_default/'
                      'bgp_routers/6004/bgp_neighbors')
path_bgp_neighbors_id = ('/rest/v1/system/vrfs/vrf_default/' +
                         'bgp_routers/6004/bgp_neighbors/' +
                         '172.17.0.3')

SWITCH_IP = None
cookie_header = None
proxy = None


def post_setup():
    status_code, response_data = execute_request(
        path_bgp, "POST", json.dumps(_DATA),
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.CREATED

    status_code, response_data = execute_request(
        path_bgp_neighbors, "POST",
        json.dumps(_DATA_BGP_NEIGHBORS), SWITCH_IP, False,
        xtra_header=cookie_header)
    assert status_code == http.client.CREATED


def delete_teardown():
    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "DELETE", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NO_CONTENT or \
        status_code == http.client.NOT_FOUND

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
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sleep(2)
    get_server_crt(sw1)
    rest_sanity_check(SWITCH_IP)


def test_restd_bgp_neighbors_get_bgp_neighbors(setup, sanity_check,
                                               topology, step):
    step("\n#####################################################\n")
    step("#               Testing GET for BGP_Neighbors       #")
    step("\n#####################################################\n")

    step('\nGET for BGP neighbors with asn: {}'.format(
        str(_DATA['configuration']['asn'])))
    status_code, response_data = execute_request(
        path_bgp_neighbors, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    step('GET for BGP neighbors with the ip: {}'.format(
        str(_DATA_BGP_NEIGHBORS['configuration']['ip_or_group_name'])))
    status_code, _response_data = execute_request(
        path_bgp_neighbors_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    d = get_json(_response_data)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = _DATA_BGP_NEIGHBORS_COPY['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_bgp_neighbors_post_bgp_neighbors(setup, sanity_check,
                                                topology, step):
    step("\n#####################################################\n")
    step("#               Testing POST for BGP_Neighbors      #")
    step("\n#####################################################\n")

    step('\nPOST BGP router with the asn: {}'.format(
        str(_DATA['configuration']['asn'])))
    status_code, response_data = execute_request(
        path_bgp, "POST", json.dumps(_DATA),
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.CREATED

    step('\nPOST BGP neighbors with the ip: {}'.format(
        str(_DATA_BGP_NEIGHBORS['configuration']['ip_or_group_name'])))
    status_code, response_data = execute_request(
        path_bgp_neighbors, "POST",
        json.dumps(_DATA_BGP_NEIGHBORS), SWITCH_IP, False,
        xtra_header=cookie_header)
    assert status_code == http.client.CREATED

    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    d = get_json(response_data)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = _DATA_BGP_NEIGHBORS_COPY['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_bgp_neighbors_put_bgp_neighbors(setup, sanity_check,
                                               topology, step):
    step("\n#####################################################\n")
    step("#               Testing PUT for BGP_Neighbors       #")
    step("\n#####################################################\n")

    aux = copy.deepcopy(_DATA_BGP_NEIGHBORS_COPY)
    aux['configuration']['description'] = 'BGP_Neighbors'

    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "PUT",
        json.dumps(aux), SWITCH_IP, False,
        xtra_header=cookie_header)
    assert status_code == http.client.OK

    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.OK

    d = get_json(response_data)
    d['configuration'].pop('capability', None)
    d = d['configuration']
    d = sorted(d.items(), key=itemgetter(0))
    aux = aux['configuration']
    aux = sorted(aux.items(), key=itemgetter(0))
    assert d == aux


def test_restd_bgp_neighbors_delete_bgp_neighbors(setup, sanity_check,
                                                  topology, step):
    step("\n#####################################################\n")
    step("#               Testing DELETE for BGP_Neighbors    #")
    step("\n#####################################################\n")

    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "DELETE", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NO_CONTENT

    status_code, response_data = execute_request(
        path_bgp_neighbors_id, "GET", None,
        SWITCH_IP, False, xtra_header=cookie_header)
    assert status_code == http.client.NOT_FOUND
