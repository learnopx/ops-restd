# -*- coding: utf-8 -*-

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.


import os
import time
from pytest import mark


TOPOLOGY = """
#
# +-------+
# |  sw1  |
# +-------+
#

# Nodes
[type=openswitch name="Switch 1"] sw1
"""

PATH = os.path.dirname(os.path.realpath(__file__))
config_files = [os.path.join(PATH, 'config1.txt'),
                os.path.join(PATH, 'config2.txt'),
                os.path.join(PATH, 'config3.txt'),
                os.path.join(PATH, 'config4.txt'),
                os.path.join(PATH, 'config5.txt'),
                os.path.join(PATH, 'config6.txt')
                ]


def reboot_switch(ops1, step):
    step("Rebooting Switch")
    onie = 'False'
    shell = 'vtysh'
    ops1.libs.reboot.reboot_switch(shell, onie)
    time.sleep(50)
    step('Rebooted')


@mark.platform_incompatible(['docker'])
def test_restd_ct_config_persistence(topology, step):

    step("\n#####################################################\n")
    step("#               Testing Config Persistence              #")
    step("\n#####################################################\n")
    sw1 = topology.get("sw1")
    assert sw1 is not None
    for fname in config_files:
        step('\nApplying Config {}'.format(fname))
        with open(fname) as f:
            lines = f.readlines()
        for line in lines:
            sw1(line.strip())
        runconfig = sw1.libs.vtysh.show_running_config()
        vtysh = sw1.get_shell('vtysh')
        vtysh.send_command('copy running-config startup-config', timeout=90)
        reboot_switch(sw1, step)
        runconfig_after_reboot = sw1.libs.vtysh.show_running_config()
        assert runconfig == runconfig_after_reboot
        sw1('erase startup-config')
        reboot_switch(sw1, step)
