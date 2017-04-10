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
    assert retStruct.returnCode() == 0, 'Failed to configure IP on\
    workstation'
    LogOutput('info', '### Successfully configured IP on workstation ###\n')
    cmdOut = wrkston01.cmd("ifconfig " + wrkston01.linkPortMapping['lnk01'])
    LogOutput('info', '### Ifconfig info for workstation 1:\n' + cmdOut + '\
    ###\n')
    retStruct = GetLinuxInterfaceIp(deviceObj=wrkston01)
    assert retStruct.returnCode() == 0, 'Failed to get linux interface\
    ip on switch'
    LogOutput('info', '### Successful in getting linux interface ip on the\
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
    LogOutput('info', '### Unconfigured IP address on dut01 port  ###\n')
    cmdOut = dut01.cmdVtysh(command="show run")
    LogOutput('info', 'Running config of the switch:\n' + cmdOut)
    retStruct = returnStruct(returnCode=0)
    return retStruct


def restTestFansid(wrkston01):
    data = {
        "configuration": {
            "direction": "f2b",
            "other_config": {
                "key": "fan_speed_override"},
            "speed": "fast",
            "external_ids": {}}}
    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system/subsystems/base/fans/base-2R",
        method="PUT",
        data=data)
    assert retStruct.returnCode(
    ) == 0, 'Failed to Execute rest command \
    "PUT for url=/rest/v1/system/subsystems/base/fans/base-2R"'
    LogOutput('info', '### Success in executing the rest command  "PUT \
    for url=/rest/v1/system/subsystems/base/fans/base-2R" ###\n')
    LogOutput('info', 'http return code ' + retStruct.data['http_retcode'])
    assert retStruct.data['http_retcode'].find(
        '200') != -1, 'Rest PUT Fanid Failed for base-2R\n' +\
        retStruct.data['response_body']
    LogOutput('info', '### Success in Rest Fanid PUT method for base-2R###\n')
    LogOutput('info', '###' + retStruct.data['response_body'] + '###\n')
    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system/subsystems/base/fans/base-2R",
        method="GET")
    assert retStruct.returnCode(
    ) == 0, 'Failed to Execute rest command \
    "GET for url=/rest/v1/system/subsystems/base/fans/base-2R"'
    LogOutput('info', '### Success in executing the rest command \
    "GET for url=/rest/v1/system/subsystems/base/fans/base-2R" ###\n')
    LogOutput('info', 'http return code ' + retStruct.data['http_retcode'])
    assert retStruct.data['http_retcode'].find(
        '200') != -1, 'Rest GET Fansid Failed\n' +\
        retStruct.data['response_body']
    LogOutput('info', '### Success in Rest GET Fansid ###\n')
    LogOutput('info', '###' + retStruct.data['response_body'] + '###\n')
    json_data = retStruct.data['response_body']
    data_dict = json.loads(json_data)
    data_config = data_dict["configuration"]
    data_otherconfig = data_config["other_config"]
    assert data_config[
        "speed"] == 'normal', 'Failed in checking the GET METHOD JSON\
         response validation for Fan speed'
    LogOutput('info', '### Success in Rest GET system for Fan speed ###\n')
    assert data_otherconfig[
        "key"] == 'fan_speed_override', 'Failed in checking the GET METHOD\
        JSON response validation for Fan Key'
    LogOutput('info', '### Success in Rest GET system for Fan Key ###\n')
    assert data_config[
        "direction"] == 'f2b', 'Failed in checking the GET METHOD JSON\
        response validation for Fan Direction'
    LogOutput('info', '### Success in Rest GET system for Fan Direction ###\n')
    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system/subsystems/base/fans/base-2R",
        method="DELETE")
    assert retStruct.returnCode(
    ) == 0, 'Failed to Execute rest command \
    "DELET for url=/rest/v1/system/subsystems/base/fans/base-2R"'
    LogOutput('info', '### Success in executing the rest command \
    "DELETE for url=/rest/v1/system/subsystems/base/fans/base-2R" ###\n')
    LogOutput('info', 'http return code ' + retStruct.data['http_retcode'])
    assert retStruct.data['http_retcode'].find(
        '204') != -1, 'Rest DELETE Fansid Failed\n' +\
        retStruct.data['response_body']
    LogOutput('info', '### Success in Rest DELETE Fansid ###\n')
    LogOutput('info', '###' + retStruct.data['response_body'] + '###\n')
    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system/subsystems/base/fans/base-2R",
        method="GET")
    assert retStruct.returnCode(
    ) == 0, '"Success in executing the rest command" \
    "GET as not expected url=/rest/v1/system/subsystems/base/fans/base-2RL"'
    LogOutput('info', '### Failed to Execute rest command \
    "GET as expected url=/rest/v1/system/subsystems/base/fans/base-2R" ###\n')
    LogOutput('info', 'http return code ' + retStruct.data['http_retcode'])
    assert retStruct.data['http_retcode'].find(
        '404') != -1, 'Rest GET method not return code 404 Fansid Failed\n' +\
        retStruct.data['response_body']
    LogOutput('info', '### Success in Rest GET method with http code 404\
    Fansid ###\n')
    LogOutput('info', '###' + retStruct.data['response_body'] + '###\n')
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
        assert retStruct.returnCode() == 0, 'Failed to config REST environment'
        LogOutput('info', '### Successful in config REST environment ###\n')

    def test_restTestFansid(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '### Testing REST Fanid basic functionality ###\n')
        LogOutput('info', '##############################################\n')
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = restTestFansid(wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to test rest Fansid'
        LogOutput('info', '### Successful in test rest Fansid ###\n')

    def test_clean_up_devices(self):
        LogOutput('info', '##############################################\n')
        LogOutput('info', '###  Device Cleanup - rolling back config  ###\n')
        LogOutput('info', '##############################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = deviceCleanup(dut01Obj, wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to cleanup device'
        LogOutput('info', '### Successfully Cleaned up devices ###\n')
