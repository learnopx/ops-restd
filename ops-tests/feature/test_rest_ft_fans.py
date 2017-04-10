# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from time import sleep
from topology_common.ops.configuration_plane.rest.rest \
    import create_certificate_and_copy_to_host
from pytest import mark
from datetime import datetime

TOPOLOGY = """
#               +-------+
# +-------+     |       |
# |  sw1  <----->   h1  |
# +-------+     |       |
#               +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=host name="Host 1"] h1

# Ports
# [force_name=oobm] sw1:sp1

# Links
sw1:if01 -- h1:if01
"""

switchmgmtaddr = "10.10.10.2"
restclientaddr = "10.10.10.3"
# REST AUTHENTICATION
USER = 'netop'
PASSWORD = 'netop'
CRT_DIRECTORY_HS = "/usr/local/share/ca-certificates/server.crt"
PROTOCOL = 'https'
PORT = '443'
LOGIN_RESULT = 200
GET_RESULT = 200


def switch_reboot(dut01):
    print("Reboot switch")
    print('###  Reboot switch  ###\n')
    dut01.libs.reboot.reboot_switch()


def config_rest_environment(dut01, wrkston01):
    global switchmgmtaddr
    global restclientaddr
    h1p1 = wrkston01.ports['if01']
    print('### Successful in getting linux interface ip on the switch ###\n')
    dut01("configure terminal")
    dut01("interface mgmt")
    dut01("ip static %s/24" % switchmgmtaddr)
    dut01("end")

    print('### Successfully configured ip on switch port ###\n')
    cmdout = dut01("show run")
    print('### Running config of the switch:\n' + cmdout + '###\n')
    print('### Configuring workstations ###\n')
    wrkston01.libs.ip.interface('if01', addr='%s/24' % restclientaddr, up=True)

    print('### Successfully configured IP on workstation ###\n')
    cmdout = wrkston01("ifconfig {h1p1}".format(**locals()))
    print('### Ifconfig info for workstation 1:\n' + cmdout + '\###\n')


def devicecleanup(dut01, wrkston01):
    h1p1 = wrkston01.ports['if01']

    wrkston01.libs.ip.remove_ip("if01", addr="%s/24" % restclientaddr)

    print('### Successfully unconfigured ip on Workstation ###\n')
    cmdout = wrkston01("ifconfig {h1p1}".format(**locals()))
    print('### Ifconfig info for workstation 1:\n' + cmdout + '\###')
    dut01("configure terminal")
    dut01("interface mgmt")
    dut01("no ip static %s/24" % switchmgmtaddr)
    dut01("end")

    print('### Unconfigured IP address on dut01 port " ###\n')
    dut01("show run")


def resttestfans(wrkston01):
    wrkston01.libs.openswitch_rest.set_server(switchmgmtaddr, PROTOCOL, PORT)
    wrkston01("echo; unset https_proxy")

    wrkston01.libs.ping.ping(5, switchmgmtaddr)
    sleep(5)
    login_result = wrkston01.libs.openswitch_rest.login_post(USER, PASSWORD,
                                                             CRT_DIRECTORY_HS,
                                                             5)
    assert login_result.get('status_code') == LOGIN_RESULT
    get_result = \
        wrkston01.libs.openswitch_rest.system_subsystems_pid_fans_id_get("base", "", https=CRT_DIRECTORY_HS,  # noqa
                                                                         request_timeout=5,  # noqa
                                                                         cookies=login_result.get('cookies'))  # noqa
    print('### Success in executing the rest command \
          "GET for url=/rest/v1/system/subsystems/base/fans" ###\n')
    print('### Success in Rest GET fans ###\n')
    assert "/rest/v1/system/subsystems/base/fans/base-1R" in \
        get_result["content"], 'Fail in checking the GET METHOD JSON response'\
        ' validation for Fan base-1R'
    print('### Success in Rest GET for Fan base-1R ###\n')
    assert "/rest/v1/system/subsystems/base/fans/base-5R" in \
        get_result["content"], 'Fail in checking the GET METHOD JSON response'\
        ' validation for Fan base-5R'
    print('### Success in Rest GET for Fan base-5R ###\n')
    assert "/rest/v1/system/subsystems/base/fans/base-2R" in \
        get_result["content"], 'Fail in checking the GET METHOD JSON response'\
        ' validation for Fan base-2R'
    print('### Success in Rest GET for Fan base-2R ###\n')
    assert "/rest/v1/system/subsystems/base/fans/base-3L" in \
        get_result["content"], 'Fail in checking the GET METHOD JSON response'\
        ' validation for Fan base-3L'
    print('### Success in Rest GET for Fan base-3L ###\n')
    assert "/rest/v1/system/subsystems/base/fans/base-4L" in \
        get_result["content"], 'Fail in checking the GET METHOD JSON response'\
        ' validation for Fan base-4L'
    print('### Success in Rest GET for Fan base-4L ###\n')


@mark.platform_incompatible(['docker'])
def test_ft_fans_framework_rest(topology, step):
    sw1 = topology.get('sw1')
    h1 = topology.get('h1')
    date = str(datetime.now())
    sw1.send_command('date --set="%s"' % date, shell='bash')
    assert sw1 is not None
    assert h1 is not None
    sw1.send_command('systemctl restart restd', shell='bash')
    print('##############################################\n')
    step('###           Reboot the switch            ###\n')
    print('##############################################\n')
    # switch_reboot(sw1)
    print('### Successful in Switch Reboot piece ###\n')

    print('##############################################\n')
    step('###       Configure REST environment       ###\n')
    print('##############################################\n')
    config_rest_environment(sw1, h1)
    print('### Successful in config REST environment  ###\n')

    print('##############################################\n')
    step('### Testing REST Fans basic functionality  ###\n')
    print('##############################################\n')
    create_certificate_and_copy_to_host(sw1, switchmgmtaddr, restclientaddr,
                                        step=step)
    sw1.send_command('systemctl restart nginx', shell='bash')
    resttestfans(h1)
    print('### Successful in test rest Fans ###\n')

    print('##############################################\n')
    step('###  Device Cleanup - rolling back config  ###\n')
    print('##############################################\n')
    devicecleanup(sw1, h1)
    print('### Successfully Cleaned up devices ###\n')
