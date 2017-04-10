# (C) Copyright 2015 Hewlett Packard Enterprise Development LP
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
#
import pytest
import json
from opstestfw.switch.CLI import *
from opstestfw import *
topoDict = {"topoType": "physical",
            "topoExecution": 3000,
            "topoDevices": "dut01 wrkston01",
            "topoLinks": "lnk01:dut01:wrkston01",
            "topoFilters": "dut01:system-category:switch,\
                            wrkston01:system-category:workstation,\
                            wrkston01:docker-image:host/freeradius-ubuntu",
            "topoLinkFilter": "lnk01:dut01:interface:eth0"}
switchMgmtAddr = "10.10.10.2"
restClientAddr = "10.10.10.3"


def switch_reboot(dut01):
    # Reboot switch
    LogOutput('info', '###  Reboot switch  ###\n')
    dut01.Reboot()
    rebootRetStruct = returnStruct(returnCode=0)
    return rebootRetStruct


def config_rest_environment(dut01, wrkston01):
    global switchMgmtAddr
    global restClientAddr
    retStruct = GetLinuxInterfaceIp(deviceObj=dut01)
    assert retStruct.returnCode() == 0, 'Failed to get linux interface\
    ip on switch'
    LogOutput('info', '### Successful in getting linux interface ip on\
    the switch ###\n')
    switchIpAddr = retStruct.data
    retStruct = InterfaceIpConfig(deviceObj=dut01,
                                  interface="mgmt",
                                  addr=switchMgmtAddr, mask=24, config=True)
    assert retStruct.returnCode() == 0, 'Failed to configure IP on switchport'
    LogOutput('info', '### Successfully configured ip on switch port ###\n')
    cmdOut = dut01.cmdVtysh(command="show run")
    LogOutput('info', '### Running config of the switch:\n' + cmdOut + '\
    ###\n')
    LogOutput('info', '### Configuring workstations ###\n')
    retStruct = wrkston01.NetworkConfig(
        ipAddr=restClientAddr,
        netMask="255.255.255.0",
        broadcast="140.1.2.255",
        interface=wrkston01.linkPortMapping['lnk01'],
        config=True)
    assert retStruct.returnCode() == 0, 'Failed to config IP on workstation'
    LogOutput('info', '### Successfully configured IP on workstation ###\n')
    cmdOut = wrkston01.cmd("ifconfig " + wrkston01.linkPortMapping['lnk01'])
    LogOutput('info', '### Ifconfig info for workstation 1:\n' + cmdOut + '\
    ###\n')
    retStruct = GetLinuxInterfaceIp(deviceObj=wrkston01)
    assert retStruct.returnCode() == 0, 'Failed to get linux interface\
    ip on switch'
    LogOutput('info', '### Successful in getting linux interface ip on \
    workstation ###\n')
    switchIpAddr = retStruct.data
    retStruct = returnStruct(returnCode=0)
    return retStruct


def deviceCleanup(dut01, wrkston01):
    retStruct = wrkston01.NetworkConfig(
        ipAddr=restClientAddr,
        netMask="255.255.255.0",
        broadcast="140.1.2.255",
        interface=wrkston01.linkPortMapping['lnk01'],
        config=False)
    assert retStruct.returnCode() == 0, 'Failed to unconfigure IP address\
    on workstation 1'
    LogOutput('info', '### Successfully unconfigured ip on Workstation ###\n')
    cmdOut = wrkston01.cmd("ifconfig " + wrkston01.linkPortMapping['lnk01'])
    LogOutput('info', '### Ifconfig info for workstation 1:\n' + cmdOut + '\
    ###')
    retStruct = InterfaceIpConfig(deviceObj=dut01,
                                  interface="mgmt",
                                  addr=switchMgmtAddr, mask=24, config=False)
    assert retStruct.returnCode() == 0, 'Failed to unconfigure IP address\
    on dut01 port'
    LogOutput('info', '### Unconfigured IP address on dut01 port " ###\n')
    cmdOut = dut01.cmdVtysh(command="show run")
    LogOutput('info', 'Running config of the switch:\n' + cmdOut)
    retStruct = returnStruct(returnCode=0)
    return retStruct


def restTestFans(wrkston01):
    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system/subsystems/base/fans",
        method="GET")
    assert retStruct.returnCode() == 0, 'Failed to Execute rest command \
    "GET for url=/rest/v1/system/subsystems/base/fans"'
    LogOutput('info', '### Success in executing the rest command \
    "GET for url=/rest/v1/system/subsystems/base/fans" ###\n')
    LogOutput('info', 'http return code ' + retStruct.data['http_retcode'])

    assert retStruct.data['http_retcode'].find('200') != -1, 'Rest GET \
    fans Failed\n' + retStruct.data['response_body']
    LogOutput('info', '### Success in Rest GET fans ###\n')
    LogOutput('info', '###' + retStruct.data['response_body'] + '###\n')
    assert retStruct.data["response_body"].find('/fans/base-3L') != -1, 'Fail\
    in checking the GET METHOD JSON response validation for Fan base-3L'
    LogOutput('info', '### Success in Rest GET for Fan base-3L ###\n')
    assert retStruct.data["response_body"].find('/fans/base-4L') != -1, 'Fail\
    in checking the GET METHOD JSON response validation for Fan base-4L'
    LogOutput('info', '### Success in Rest GET for Fan base-4L ###\n')
    assert retStruct.data["response_body"].find('/fans/base-1R') != -1, 'Fail\
    in checking the GET METHOD JSON response validation for Fan base-1R'
    LogOutput('info', '### Success in Rest GET for Fan base-1R ###\n')
    assert retStruct.data["response_body"].find('/fans/base-2R') != -1, 'Fail\
    in checking the GET METHOD JSON response validation for Fan base-2R'
    LogOutput('info', '### Success in Rest GET for Fan base-2R ###\n')
    assert retStruct.data["response_body"].find('/fans/base-5R') != -1, 'Fail\
    in checking the GET METHOD JSON response validation for Fan base-5R'
    LogOutput('info', '### Success in Rest GET for Fan base-5R ###\n')
    retStruct = returnStruct(returnCode=0)
    return retStruct


class Test_ft_framework_rest:

    def setup_class(cls):
        # Create Topology object and connect to devices
        Test_ft_framework_rest.testObj = testEnviron(topoDict=topoDict)
        Test_ft_framework_rest.topoObj = \
            Test_ft_framework_rest.testObj.topoObjGet()
        wrkston01Obj = Test_ft_framework_rest.topoObj.deviceObjGet(
            device="wrkston01")
        wrkston01Obj.CreateRestEnviron()

    def teardown_class(cls):
        # Terminate all nodes
        Test_ft_framework_rest.topoObj.terminate_nodes()

    def test_reboot_switch(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '###           Reboot the switch            ###\n')
        LogOutput('info', '##############################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        retStruct = switch_reboot(dut01Obj)
        assert retStruct.returnCode() == 0, 'Failed to reboot Switch'
        LogOutput('info', '### Successful in Switch Reboot piece ###\n')

    def test_config_rest_environment(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '###       Configure REST environment       ###\n')
        LogOutput('info', '##############################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = config_rest_environment(dut01Obj, wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Fail to config REST environment'
        LogOutput('info', '### Successful in config REST environment  ###\n')

    def test_restTestFans(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '### Testing REST Fans basic functionality  ###\n')
        LogOutput('info', '##############################################\n')
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = restTestFans(wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to test rest Fans'
        LogOutput('info', '### Successful in test rest Fans ###\n')

    def test_clean_up_devices(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '###  Device Cleanup - rolling back config  ###\n')
        LogOutput('info', '##############################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = deviceCleanup(dut01Obj, wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to cleanup device'
        LogOutput('info', '### Successfully Cleaned up devices ###\n')
