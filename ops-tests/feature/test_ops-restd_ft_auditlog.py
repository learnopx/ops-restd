# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Openswitch Test for Auditlog
"""

import pytest
import http.client
from pytest import mark


TOPOLOGY = """
# +-------+      +-------+
# |  hs1   <----->  ops1  |
# +-------+      +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] ops1
[type=host name="Host 1"] hs1
[force_name=oobm] ops1:1

# Links
hs1:1 -- ops1:1
"""


DEFAULT_USER = 'netop'
DEFAULT_PASSWORD = 'netop'
switch_ip = '10.0.10.1'
host_ip = '10.0.10.100'
mask = '24'
cookie = None


def fast_clean_auditlog(ops1):
    ops1('echo > /var/log/audit/audit.log;', shell='bash')


def curl_event(rest_server_ip, method, url, command, cookie=None, data=None):
    '''
    Generates the curl command.
    This method should be replaced whenthe REST library for the
    Modular Test Framework is available.
    '''
    curl_command = ('curl -v -k -H \"Content-Type: application/json\" '
                    '--retry 3 ')
    curl_xmethod = '-X ' + method + ' '
    curl_url = '\"https://' + rest_server_ip + url + '\" '
    curl_command += curl_xmethod

    if (cookie):
        curl_command += '--cookie \'' + cookie + '\' '
    if (data):
        curl_command += '-d \'' + data + '\' '

    curl_command += curl_url

    if (command):
        curl_command += command

    return curl_command


@pytest.fixture
def get_login_cookie(topology):
    '''
    Method returns the login cookie by parsing the curl output
    '''
    hs1 = topology.get('hs1')
    login_curl = curl_event(switch_ip, 'POST',
                            '/login?username=' + DEFAULT_USER +
                            ';password=' + DEFAULT_PASSWORD,
                            '2>&1 | grep Set-Cookie')
    login_post = hs1(login_curl, shell='bash')
    global cookie
    cookie = login_post[login_post.index('user='):]
    assert len(cookie) > 0, "The login cookie is invalid"


def get_status_code(request_output):
    '''
    Method returns the status code by parsing the curl output
    '''
    request_output = request_output.split('\n')[1]
    return int(request_output[request_output.index('HTTP/1.1'):].split(' ')[1])


def auditlog_ausearch_verification(switch, data):
    ausearch = switch('ausearch -i', shell='bash').split('\n')
    for line in ausearch:
        if ('type=USYS_CONFIG' in line and data['operation'] in line):
            assert 'user=' + DEFAULT_USER in line, 'Wrong User'
            assert data['result'] in line, 'Wrong result'
            assert 'addr=' + host_ip in line, 'Wrong host ip address'


@pytest.fixture(scope="module")
@mark.platform_incompatible(['docker'])
def setup(topology, request):
    """
    Set network address
    """
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')

    assert ops1 is not None
    assert hs1 is not None

    # Configure IP and bring UP host 1 interface and ops 1 interface
    with ops1.libs.vtysh.ConfigInterfaceMgmt() as ctx:
        ctx.ip_static(switch_ip + '/' + mask)
    hs1.libs.ip.interface('1', addr=host_ip + '/' + mask, up=True)

    # Clean bridges
    bridges = ops1('list-br', shell='vsctl').split('\n')
    for bridge in bridges:
        if bridge != 'bridge_normal':
            ops1('del-br {bridge}'.format(**locals()), shell='vsctl')

    def fin():
        with ops1.libs.vtysh.ConfigInterfaceMgmt() as ctx:
            ctx.no_ip_static(switch_ip + '/' + mask)
        hs1.libs.ip.remove_ip('1', addr=host_ip + '/' + mask)

    request.addfinalizer(fin)


@mark.platform_incompatible(['docker'])
def test_auditlog_post_login(topology, setup):
    # Test 1. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    fast_clean_auditlog(ops1)

    login_curl = curl_event(switch_ip, 'POST',
                            '/login?username=' + DEFAULT_USER +
                            ';password=' + DEFAULT_PASSWORD,
                            '2>&1 | grep Set-Cookie')
    login_post = hs1(login_curl, shell='bash')
    cookie = login_post[login_post.index('user='):]
    assert len(cookie) > 0, "The login cookie is invalid"

    # Test 1. Verify in Auditlog / Ausearch the Login event
    expected_data = {'operation': 'op=RESTD:POST', 'result': 'res=success'}
    auditlog_ausearch_verification(ops1, expected_data)


@mark.platform_incompatible(['docker'])
def test_auditlog_post_bridge_success(topology, setup, get_login_cookie):
    # Test 2. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    fast_clean_auditlog(ops1)
    post_bridge = curl_event(switch_ip, 'POST',
                             '/rest/v1/system/bridges',
                             '2>&1 | grep "< HTTP/1.1 "', cookie,
                             '{"configuration": '
                             '{"datapath_type": "", "name": "br0"}}')

    # Test 2. Verify in Auditlog / Ausearch the Bridge POST event success
    status_code = get_status_code(hs1(post_bridge, shell='bash'))
    assert status_code == http.client.CREATED, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:POST', 'result': 'res=success'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 2. Teardown
    ops1('del-br br0', shell='vsctl')


@mark.platform_incompatible(['docker'])
def test_auditlog_post_bridge_failed(topology, setup, get_login_cookie):
    # Test 3. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    post_bridge = curl_event(switch_ip, 'POST',
                             '/rest/v1/system/bridges',
                             '2>&1 | grep "< HTTP/1.1 "', cookie,
                             '{"configuration": '
                             '{"datapath_type": "", "name": "br0"}}')

    # Test 3. Verify in Auditlog / Ausearch the Bridge POST event failed
    status_code = get_status_code(hs1(post_bridge, shell='bash'))
    assert status_code == http.client.BAD_REQUEST, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:POST', 'result': 'res=failed'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 3. Teardown
    ops1('del-br br0', shell='vsctl')


@mark.platform_incompatible(['docker'])
def test_auditlog_put_bridge_success(topology, setup, get_login_cookie):
    # Test 4. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    put_bridge = curl_event(switch_ip, 'PUT',
                            '/rest/v1/system/bridges/br0',
                            '2>&1 | grep "< HTTP/1.1 "', cookie,
                            '{"configuration": '
                            '{"datapath_type": "bridge", "name": "br0"}}')

    # Test 4. Verify in Auditlog / Ausearch the Bridge PUT event success
    status_code = get_status_code(hs1(put_bridge, shell='bash'))
    assert status_code == http.client.OK, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:PUT', 'result': 'res=success'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 4. Teardown
    ops1('del-br br0', shell='vsctl')


@mark.platform_incompatible(['docker'])
def test_auditlog_put_bridge_failed(topology, setup, get_login_cookie):
    # Test 5. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    put_bridge = curl_event(switch_ip, 'PUT',
                            '/rest/v1/system/bridges',
                            '2>&1 | grep "< HTTP/1.1 "', cookie,
                            '{"configuration": '
                            '{"datapath_type": "bridge", "name": "br0"}}')

    # Test 5. Verify in Auditlog / Ausearch the Bridge PUT event failed
    status_code = get_status_code(hs1(put_bridge, shell='bash'))
    assert status_code == http.client.METHOD_NOT_ALLOWED, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:PUT', 'result': 'res=failed'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 5. Teardown
    ops1('del-br br0', shell='vsctl')


@mark.platform_incompatible(['docker'])
def test_auditlog_delete_bridge_success(topology, setup, get_login_cookie):
    # Test 6. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    delete_bridge = curl_event(switch_ip, 'DELETE',
                               '/rest/v1/system/bridges/br0',
                               '2>&1 | grep "< HTTP/1.1 "', cookie)

    # Test 6. Verify in Auditlog / Ausearch the Bridge DELETE event success
    status_code = get_status_code(hs1(delete_bridge, shell='bash'))
    assert status_code == http.client.NO_CONTENT, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:DELETE', 'result': 'res=success'}
    auditlog_ausearch_verification(ops1, expected_data)


@mark.platform_incompatible(['docker'])
def test_auditlog_delete_bridge_failed(topology, setup, get_login_cookie):
    # Test 7. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    fast_clean_auditlog(ops1)
    delete_bridge = curl_event(switch_ip, 'DELETE',
                               '/rest/v1/system/bridges/br100',
                               '2>&1 | grep "< HTTP/1.1 "', cookie)

    # Test 7. Verify in Auditlog / Ausearch the Bridge DELETE event failed
    status_code = get_status_code(hs1(delete_bridge, shell='bash'))
    assert status_code == http.client.NOT_FOUND, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:DELETE', 'result': 'res=failed'}
    auditlog_ausearch_verification(ops1, expected_data)


@mark.platform_incompatible(['docker'])
def test_auditlog_patch_bridge_success(topology, setup, get_login_cookie):
    # Test 8. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    put_bridge = curl_event(switch_ip, 'PATCH',
                            '/rest/v1/system/bridges/br0',
                            '2>&1 | grep "< HTTP/1.1 "', cookie,
                            '[{"op": "add", "path": "/datapath_type", '
                            '"value": "bridge"}]')

    # Test 8. Verify in Auditlog / Ausearch the Bridge PATCH event success
    status_code = get_status_code(hs1(put_bridge, shell='bash'))
    assert status_code == http.client.NO_CONTENT, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:PATCH', 'result': 'res=success'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 8. Teardown
    ops1('del-br br0', shell='vsctl')


@mark.platform_incompatible(['docker'])
def test_auditlog_patch_bridge_failed(topology, setup, get_login_cookie):
    # Test 9. Setup
    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    ops1('add-br br0', shell='vsctl')
    fast_clean_auditlog(ops1)
    put_bridge = curl_event(switch_ip, 'PATCH',
                            '/rest/v1/system/bridges/br0',
                            '2>&1 | grep "< HTTP/1.1 "', cookie,
                            '[{"op": "add", "path": "/nonexistent_path", '
                            '"value": "bridge"}]')

    # Test 9. Verify in Auditlog / Ausearch the Bridge PATCH event failed
    status_code = get_status_code(hs1(put_bridge, shell='bash'))
    assert status_code == http.client.BAD_REQUEST, 'Wrong status code'

    expected_data = {'operation': 'op=RESTD:PATCH', 'result': 'res=failed'}
    auditlog_ausearch_verification(ops1, expected_data)

    # Test 9. Teardown
    ops1('del-br br0', shell='vsctl')
