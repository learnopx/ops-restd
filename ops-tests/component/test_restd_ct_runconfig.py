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

import os
import pytest
from shutil import copy2
from random import randint

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


'''
This script copies user config files(config_test1.db, config_test2.db,
empty_config.db) and runconfig_test_in_docker.py onto the switch. The
runconfig_test_in_docker.py verifies if the user config is written
successfully to the OVSDB.
'''


def copy_to_docker(step):
    step("\n########## Copying required files to docker ##########\n")
    src_path = os.path.dirname(os.path.realpath(__file__))
    testid = randint(1, 10000)
    script_shared_local = '/tmp/openswitch-test/{}/' \
        'shared/runconfig_test_in_docker.py'.format(testid)
    # script_shared_local_runconfig = '/tmp/openswitch-test/{}/' \
    #     'shared/runconfig.py'.format(testid)
    script_shared_test_file1 = '/tmp/openswitch-test/{}/' \
        'shared/config_test1'.format(testid)
    script_shared_test_file2 = '/tmp/openswitch-test/{}/' \
        'shared/config_test2'.format(testid)
    script_shared_test_file3 = '/tmp/openswitch-test/{}/' \
        'shared/empty_config.db'.format(testid)

    copy2(os.path.join(src_path, "runconfig_test_in_docker.py"),
          script_shared_local)
    copy2(os.path.join(src_path, "config_test1.db"),
          script_shared_test_file1)
    copy2(os.path.join(src_path, "config_test2.db"),
          script_shared_test_file2)
    copy2(os.path.join(src_path, "empty_config.db"),
          script_shared_test_file3)


def verify_runconfig(switch, step):
    step('########################################################\n')
    step('###### Testing full config and empty config   ######\n')
    step('########################################################\n')
    script_shared_docker = '/shared/runconfig_test_in_docker.py'
    out = switch('python {}'.format(script_shared_docker))
    res = out.find("Test Failure")
    assert res == -1


@pytest.mark.skipif(True, reason="Disabling until this test is fixed "
                                 "for the current schema")
def test_restd_ct_runconfig(topology, step):
    switch = topology.get("sw1")
    assert switch is not None
    copy_to_docker(step)
    verify_runconfig(switch, step)
