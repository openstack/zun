# Copyright 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import six

from mock import mock_open
from oslo_serialization import jsonutils

from zun.common import exception
from zun.container.os_capability.linux import os_capability_linux
from zun.tests import base

LSCPU_ON = """# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# Socket,CPU,Online
0,0,Y
0,8,Y
1,16,Y
1,24,Y
2,32,Y"""

LSCPU_NO_ONLINE = """# The following is the parsable format, which can be fed to
# programs. Each different item in every column has an unique ID
# starting from zero.
# Socket,CPU
0,0
0,1
1,2
1,3"""


class TestOSCapability(base.BaseTestCase):
    @mock.patch('zun.common.utils.execute')
    def test_get_cpu_numa_info_with_online(self, mock_output):
        mock_output.return_value = LSCPU_ON
        output = os_capability_linux.LinuxHost().get_cpu_numa_info()
        expected_output = {'0': [0, 8], '1': [16, 24], '2': [32]}
        self.assertEqual(expected_output, output)

    @mock.patch('zun.common.utils.execute')
    def test_get_cpu_numa_info_exception(self, mock_output):
        mock_output.side_effect = exception.CommandError()
        self.assertRaises(exception.CommandError,
                          os_capability_linux.LinuxHost().get_cpu_numa_info)

    @mock.patch('zun.common.utils.execute')
    def test_get_cpu_numa_info_without_online(self, mock_output):
        mock_output.side_effect = [exception.CommandError(),
                                   LSCPU_NO_ONLINE]
        expected_output = {'0': [0, 1], '1': [2, 3]}
        output = os_capability_linux.LinuxHost().get_cpu_numa_info()
        self.assertEqual(expected_output, output)

    def test_get_host_mem(self):
        data = ('MemTotal:        3882464 kB\nMemFree:         3514608 kB\n'
                'MemAvailable:    3556372 kB\n')
        m_open = mock_open(read_data=data)
        with mock.patch.object(six.moves.builtins, "open", m_open,
                               create=True):
            output = os_capability_linux.LinuxHost().get_host_mem()
            used = (3882464 - 3556372)
            self.assertEqual((3882464, 3514608, 3556372, used), output)

    @mock.patch('zun.pci.utils.get_ifname_by_pci_address')
    @mock.patch('zun.pci.utils.get_net_name_by_vf_pci_address')
    @mock.patch('zun.common.utils.execute')
    def test_get_pci_resource(self, mock_output, mock_netname,
                              mock_ifname):
        mock_netname.return_value = 'net_enp2s0f3_ec_38_8f_79_11_2b'
        mock_ifname.return_value = 'enp2s0f3'
        value1 = '''0000:02:10.7 "Ethernet controller...." ""'''
        value2 = '02:10.7 0200: 8086:1520 (rev 01)'
        value3 = '''Slot:   02:10.7
        Class:  Ethernet controller
        Vendor: Intel Corporation
        Device: I350 Ethernet Controller Virtual Function
        Rev:    01
        NUMANode:   0'''
        value4 = 'class physfn'
        value5 = '''DRIVER=igbvf
        PCI_CLASS=20000
        PCI_ID=8086:1520
        PCI_SUBSYS_ID=FFFF:0000
        PCI_SLOT_NAME=0000:02:10.7
        MODALIAS=pci:v00008086d00001520sv0000FFFFsd00000000bc02sc00i00'''
        value6 = '''Features for enp2s0f3:
rx-checksumming: on
tx-checksumming: on
scatter-gather: on
tcp-segmentation-offload: on
generic-receive-offload: on
large-receive-offload: off [fixed]
rx-vlan-offload: on
tx-vlan-offload: on
ntuple-filters: off [fixed]
receive-hashing: on
highdma: on [fixed]
rx-vlan-filter: on [fixed]
vlan-challenged: off [fixed]
tx-lockless: off [fixed]
netns-local: off [fixed]
tx-gso-robust: off [fixed]
tx-fcoe-segmentation: off [fixed]
tx-gre-segmentation: off [fixed]
tx-ipip-segmentation: off [fixed]
tx-sit-segmentation: off [fixed]
tx-udp_tnl-segmentation: off [fixed]
tx-mpls-segmentation: off [fixed]
rx-fcs: off [fixed]
tx-vlan-stag-hw-insert: off [fixed]
rx-vlan-stag-hw-parse: off [fixed]
rx-vlan-stag-filter: off [fixed]'''
        values = [(value1, 0),
                  (value2, 0),
                  (value3, 0),
                  (value4, 0),
                  (value5, 0),
                  (value6, 0)]
        mock_output.side_effect = values
        expected = {"dev_id": "pci_0000_02_10_7",
                    "address": "0000:02:10.7",
                    "vendor_id": "8086",
                    "product_id": "1520",
                    "numa_node": 0,
                    "label": "label_8086_1520",
                    "dev_type": "VF",
                    "parent_addr": "0000:02:10.7"}
        output = os_capability_linux.LinuxHost().get_pci_resources()

        pci_infos = jsonutils.loads(output)
        for pci_info in pci_infos:
            self.assertEqual(expected['dev_id'], str(pci_info['dev_id']))
            self.assertEqual(expected['address'], str(pci_info['address']))
            self.assertEqual(expected['product_id'],
                             str(pci_info['product_id']))
            self.assertEqual(expected['vendor_id'], str(pci_info['vendor_id']))
            self.assertEqual(expected['numa_node'], pci_info['numa_node'])
            self.assertEqual(expected['label'], str(pci_info['label']))
            self.assertEqual(expected['dev_type'], str(pci_info['dev_type']))
            self.assertEqual(expected['parent_addr'],
                             str(pci_info['parent_addr']))
