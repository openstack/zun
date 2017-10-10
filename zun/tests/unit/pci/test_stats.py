# Copyright (c) 2017 OpenStack Foundation
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

import mock
from oslo_config import cfg

from zun.common import exception
from zun import objects
from zun.objects import fields
from zun.pci import stats
from zun.pci import whitelist
from zun.tests import base
from zun.tests.unit.pci import fakes

CONF = cfg.CONF
fake_pci_1 = {
    'compute_node_uuid': 1,
    'address': '0000:00:00.1',
    'product_id': 'p1',
    'vendor_id': 'v1',
    'status': 'available',
    'extra_k1': 'v1',
    'request_id': None,
    'numa_node': 0,
    'dev_type': fields.PciDeviceType.STANDARD,
    'parent_addr': None,
    }


fake_pci_2 = dict(fake_pci_1, vendor_id='v2',
                  product_id='p2',
                  address='0000:00:00.2',
                  numa_node=1)


fake_pci_3 = dict(fake_pci_1, address='0000:00:00.3')

fake_pci_4 = dict(fake_pci_1, vendor_id='v3',
                  product_id='p3',
                  address='0000:00:00.3',
                  numa_node=None)


class PciDeviceStatsTestCase(base.TestCase):
    def _create_fake_devs(self):
        self.fake_dev_1 = objects.PciDevice.create(None, fake_pci_1)
        self.fake_dev_2 = objects.PciDevice.create(None, fake_pci_2)
        self.fake_dev_3 = objects.PciDevice.create(None, fake_pci_3)
        self.fake_dev_4 = objects.PciDevice.create(None, fake_pci_4)

        for dev in [self.fake_dev_1, self.fake_dev_2,
                    self.fake_dev_3, self.fake_dev_4]:
            self.pci_stats.add_device(dev)

    def setUp(self):
        super(PciDeviceStatsTestCase, self).setUp()
        self.pci_stats = stats.PciDeviceStats()
        # The following two calls need to be made before adding the devices.
        patcher = fakes.fake_pci_whitelist()
        self.addCleanup(patcher.stop)
        self._create_fake_devs()

    def test_add_device(self):
        self.assertEqual(len(self.pci_stats.pools), 3)
        self.assertEqual(set([d['vendor_id'] for d in self.pci_stats]),
                         set(['v1', 'v2', 'v3']))
        self.assertEqual(set([d['count'] for d in self.pci_stats]),
                         set([1, 2]))

    def test_remove_device(self):
        self.pci_stats.remove_device(self.fake_dev_2)
        self.assertEqual(len(self.pci_stats.pools), 2)
        self.assertEqual(self.pci_stats.pools[0]['count'], 2)
        self.assertEqual(self.pci_stats.pools[0]['vendor_id'], 'v1')

    def test_remove_device_exception(self):
        self.pci_stats.remove_device(self.fake_dev_2)
        self.assertRaises(exception.PciDevicePoolEmpty,
                          self.pci_stats.remove_device,
                          self.fake_dev_2)

    def test_pci_stats_equivalent(self):
        pci_stats2 = stats.PciDeviceStats()
        for dev in [self.fake_dev_1,
                    self.fake_dev_2,
                    self.fake_dev_3,
                    self.fake_dev_4]:
            pci_stats2.add_device(dev)
        self.assertEqual(self.pci_stats, pci_stats2)

    def test_pci_stats_not_equivalent(self):
        pci_stats2 = stats.PciDeviceStats()
        for dev in [self.fake_dev_1,
                    self.fake_dev_2,
                    self.fake_dev_3]:
            pci_stats2.add_device(dev)
        self.assertNotEqual(self.pci_stats, pci_stats2)

    def test_object_create(self):
        m = self.pci_stats.to_device_pools_obj()
        new_stats = stats.PciDeviceStats(m)

        self.assertEqual(len(new_stats.pools), 3)
        self.assertEqual(set([d['count'] for d in new_stats]),
                         set([1, 2]))
        self.assertEqual(set([d['vendor_id'] for d in new_stats]),
                         set(['v1', 'v2', 'v3']))

    @mock.patch(
        'zun.pci.whitelist.Whitelist._parse_white_list_from_config')
    def test_white_list_parsing(self, mock_whitelist_parse):
        white_list = '{"product_id":"0001", "vendor_id":"8086"}'
        CONF.set_override('passthrough_whitelist', white_list, 'pci')
        pci_stats = stats.PciDeviceStats()
        pci_stats.add_device(self.fake_dev_2)
        pci_stats.remove_device(self.fake_dev_2)
        self.assertEqual(1, mock_whitelist_parse.call_count)


class PciDeviceStatsWithTagsTestCase(base.TestCase):

    def setUp(self):
        super(PciDeviceStatsWithTagsTestCase, self).setUp()
        white_list = ['{"vendor_id":"1137","product_id":"0071",'
                      '"address":"*:0a:00.*","physical_network":"physnet1"}',
                      '{"vendor_id":"1137","product_id":"0072"}']
        self.config(passthrough_whitelist=white_list, group='pci')
        dev_filter = whitelist.Whitelist(white_list)
        self.pci_stats = stats.PciDeviceStats(dev_filter=dev_filter)

    def _create_pci_devices(self):
        self.pci_tagged_devices = []
        for dev in range(4):
            pci_dev = {'compute_node_uuid': 1,
                       'address': '0000:0a:00.%d' % dev,
                       'vendor_id': '1137',
                       'product_id': '0071',
                       'status': 'available',
                       'request_id': None,
                       'dev_type': 'PCI',
                       'parent_addr': None,
                       'numa_node': 0}
            self.pci_tagged_devices.append(objects.PciDevice.create(None,
                                                                    pci_dev))

        self.pci_untagged_devices = []
        for dev in range(3):
            pci_dev = {'compute_node_uuid': 1,
                       'address': '0000:0b:00.%d' % dev,
                       'vendor_id': '1137',
                       'product_id': '0072',
                       'status': 'available',
                       'request_id': None,
                       'dev_type': 'PCI',
                       'parent_addr': None,
                       'numa_node': 0}
            self.pci_untagged_devices.append(objects.PciDevice.create(None,
                                                                      pci_dev))

        for dev in self.pci_tagged_devices:
            self.pci_stats.add_device(dev)

        for dev in self.pci_untagged_devices:
            self.pci_stats.add_device(dev)

    def _assertPoolContent(self, pool, vendor_id, product_id, count, **tags):
        self.assertEqual(vendor_id, pool['vendor_id'])
        self.assertEqual(product_id, pool['product_id'])
        self.assertEqual(count, pool['count'])
        if tags:
            for k, v in tags.items():
                self.assertEqual(v, pool[k])

    def _assertPools(self):
        # Pools are ordered based on the number of keys. 'product_id',
        # 'vendor_id' are always part of the keys. When tags are present,
        # they are also part of the keys. In this test class, we have
        # two pools with the second one having the tag 'physical_network'
        # and the value 'physnet1'
        self.assertEqual(2, len(self.pci_stats.pools))
        self._assertPoolContent(self.pci_stats.pools[0], '1137', '0072',
                                len(self.pci_untagged_devices))
        self.assertEqual(self.pci_untagged_devices,
                         self.pci_stats.pools[0]['devices'])
        self._assertPoolContent(self.pci_stats.pools[1], '1137', '0071',
                                len(self.pci_tagged_devices),
                                physical_network='physnet1')
        self.assertEqual(self.pci_tagged_devices,
                         self.pci_stats.pools[1]['devices'])

    def test_add_devices(self):
        self._create_pci_devices()
        self._assertPools()

    def test_add_device_no_devspec(self):
        self._create_pci_devices()
        pci_dev = {'compute_node_uuid': 1,
                   'address': '0000:0c:00.1',
                   'vendor_id': '2345',
                   'product_id': '0172',
                   'status': 'available',
                   'parent_addr': None,
                   'request_id': None}
        pci_dev_obj = objects.PciDevice.create(None, pci_dev)
        self.pci_stats.add_device(pci_dev_obj)
        # There should be no change
        self.assertIsNone(
            self.pci_stats._create_pool_keys_from_dev(pci_dev_obj))
        self._assertPools()

    def test_remove_device_no_devspec(self):
        self._create_pci_devices()
        pci_dev = {'compute_node_uuid': 1,
                   'address': '0000:0c:00.1',
                   'vendor_id': '2345',
                   'product_id': '0172',
                   'status': 'available',
                   'parent_addr': None,
                   'request_id': None}
        pci_dev_obj = objects.PciDevice.create(None, pci_dev)
        self.pci_stats.remove_device(pci_dev_obj)
        # There should be no change
        self.assertIsNone(
            self.pci_stats._create_pool_keys_from_dev(pci_dev_obj))
        self._assertPools()

    def test_remove_device(self):
        self._create_pci_devices()
        dev1 = self.pci_untagged_devices.pop()
        self.pci_stats.remove_device(dev1)
        dev2 = self.pci_tagged_devices.pop()
        self.pci_stats.remove_device(dev2)
        self._assertPools()


class PciDeviceVFPFStatsTestCase(base.TestCase):

    def setUp(self):
        super(PciDeviceVFPFStatsTestCase, self).setUp()
        white_list = ['{"vendor_id":"8086","product_id":"1528"}',
                      '{"vendor_id":"8086","product_id":"1515"}']
        self.config(passthrough_whitelist=white_list, group='pci')
        self.pci_stats = stats.PciDeviceStats()

    def _create_pci_devices(self, vf_product_id=1515, pf_product_id=1528):
        self.sriov_pf_devices = []
        for dev in range(2):
            pci_dev = {'compute_node_uuid': 1,
                       'address': '0000:81:00.%d' % dev,
                       'vendor_id': '8086',
                       'product_id': '%d' % pf_product_id,
                       'status': 'available',
                       'request_id': None,
                       'dev_type': fields.PciDeviceType.SRIOV_PF,
                       'parent_addr': None,
                       'numa_node': 0}
            dev_obj = objects.PciDevice.create(None, pci_dev)
            dev_obj.child_devices = []
            self.sriov_pf_devices.append(dev_obj)

        self.sriov_vf_devices = []
        for dev in range(8):
            pci_dev = {'compute_node_uuid': 1,
                       'address': '0000:81:10.%d' % dev,
                       'vendor_id': '8086',
                       'product_id': '%d' % vf_product_id,
                       'status': 'available',
                       'request_id': None,
                       'dev_type': fields.PciDeviceType.SRIOV_VF,
                       'parent_addr': '0000:81:00.%d' % int(dev / 4),
                       'numa_node': 0}
            dev_obj = objects.PciDevice.create(None, pci_dev)
            dev_obj.parent_device = self.sriov_pf_devices[int(dev / 4)]
            dev_obj.parent_device.child_devices.append(dev_obj)
            self.sriov_vf_devices.append(dev_obj)

        list(map(self.pci_stats.add_device, self.sriov_pf_devices))
        list(map(self.pci_stats.add_device, self.sriov_vf_devices))
