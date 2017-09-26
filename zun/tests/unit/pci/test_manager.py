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

import copy

import mock

import zun
from zun.common import context
from zun.objects import fields
from zun.pci import manager
from zun.tests.unit.db import base
from zun.tests.unit.pci import fakes as pci_fakes
from zun.tests import uuidsentinel


fake_pci = {
    'compute_node_uuid': 1,
    'address': '0000:00:00.1',
    'product_id': 'p',
    'vendor_id': 'v',
    'request_id': None,
    'status': fields.PciDeviceStatus.AVAILABLE,
    'dev_type': fields.PciDeviceType.STANDARD,
    'parent_addr': None,
    'numa_node': 0}
fake_pci_1 = dict(fake_pci, address='0000:00:00.2',
                  product_id='p1', vendor_id='v1')
fake_pci_2 = dict(fake_pci, address='0000:00:00.3')

fake_pci_3 = dict(fake_pci, address='0000:00:01.1',
                  dev_type=fields.PciDeviceType.SRIOV_PF,
                  vendor_id='v2', product_id='p2', numa_node=None)
fake_pci_4 = dict(fake_pci, address='0000:00:02.1',
                  dev_type=fields.PciDeviceType.SRIOV_VF,
                  parent_addr='0000:00:01.1',
                  vendor_id='v2', product_id='p2', numa_node=None)
fake_pci_5 = dict(fake_pci, address='0000:00:02.2',
                  dev_type=fields.PciDeviceType.SRIOV_VF,
                  parent_addr='0000:00:01.1',
                  vendor_id='v2', product_id='p2', numa_node=None)

fake_db_dev = {
    'created_at': None,
    'updated_at': None,
    'deleted_at': None,
    'deleted': None,
    'id': 1,
    'uuid': uuidsentinel.pci_device1,
    'compute_node_uuid': 1,
    'address': '0000:00:00.1',
    'vendor_id': 'v',
    'product_id': 'p',
    'numa_node': 1,
    'dev_type': fields.PciDeviceType.STANDARD,
    'status': fields.PciDeviceStatus.AVAILABLE,
    'dev_id': 'i',
    'label': 'l',
    'container_uuid': None,
    'extra_info': '{}',
    'request_id': None,
    'parent_addr': None,
    }
fake_db_dev_1 = dict(fake_db_dev, vendor_id='v1',
                     uuid=uuidsentinel.pci_device1,
                     product_id='p1', id=2,
                     address='0000:00:00.2',
                     numa_node=0)
fake_db_dev_2 = dict(fake_db_dev, id=3, address='0000:00:00.3',
                     uuid=uuidsentinel.pci_device2,
                     numa_node=None, parent_addr='0000:00:00.1')
fake_db_devs = [fake_db_dev, fake_db_dev_1, fake_db_dev_2]

fake_db_dev_3 = dict(fake_db_dev, id=4, address='0000:00:01.1',
                     uuid=uuidsentinel.pci_device3,
                     vendor_id='v2', product_id='p2',
                     numa_node=None, dev_type=fields.PciDeviceType.SRIOV_PF)
fake_db_dev_4 = dict(fake_db_dev, id=5, address='0000:00:02.1',
                     uuid=uuidsentinel.pci_device4,
                     numa_node=None, dev_type=fields.PciDeviceType.SRIOV_VF,
                     vendor_id='v2', product_id='p2',
                     parent_addr='0000:00:01.1')
fake_db_dev_5 = dict(fake_db_dev, id=6, address='0000:00:02.2',
                     uuid=uuidsentinel.pci_device5,
                     numa_node=None, dev_type=fields.PciDeviceType.SRIOV_VF,
                     vendor_id='v2', product_id='p2',
                     parent_addr='0000:00:01.1')
fake_db_devs_tree = [fake_db_dev_3, fake_db_dev_4, fake_db_dev_5]


class PciDevTrackerTestCase(base.DbTestCase):
    def _fake_get_pci_devices(self, node_id):
                return self.fake_devs

    def _fake_pci_device_update(self, node_id, address, value):
        self.update_called += 1
        self.called_values = value
        fake_return = copy.deepcopy(fake_db_dev)
        return fake_return

    def _fake_pci_device_destroy(self, node_id, address):
        self.destroy_called += 1

    def _create_tracker(self, fake_devs):
        self.fake_devs = fake_devs
        self.tracker = manager.PciDevTracker(self.fake_context, 1)

    def setUp(self):
        super(PciDevTrackerTestCase, self).setUp()
        self.fake_context = context.get_admin_context()
        self.fake_devs = fake_db_devs[:]
        self.stub_out('zun.db.api.get_all_pci_device_by_node',
                      self._fake_get_pci_devices)
        # The fake_pci_whitelist must be called before creating the fake
        # devices
        patcher = pci_fakes.fake_pci_whitelist()
        self.addCleanup(patcher.stop)
        self._create_tracker(fake_db_devs[:])

    def test_pcidev_tracker_create(self):
        self.assertEqual(len(self.tracker.pci_devs), 3)
        free_devs = self.tracker.pci_stats.get_free_devs()
        self.assertEqual(len(free_devs), 3)
        self.assertEqual(list(self.tracker.stale), [])
        self.assertEqual(len(self.tracker.stats.pools), 3)
        self.assertEqual(self.tracker.node_id, 1)
        for dev in self.tracker.pci_devs:
            self.assertIsNone(dev.parent_device)
            self.assertEqual(dev.child_devices, [])

    def test_pcidev_tracker_create_device_tree(self):
        self._create_tracker(fake_db_devs_tree)

        self.assertEqual(len(self.tracker.pci_devs), 3)
        free_devs = self.tracker.pci_stats.get_free_devs()
        self.assertEqual(len(free_devs), 3)
        self.assertEqual(list(self.tracker.stale), [])
        self.assertEqual(len(self.tracker.stats.pools), 2)
        self.assertEqual(self.tracker.node_id, 1)
        pf = [dev for dev in self.tracker.pci_devs
              if dev.dev_type == fields.PciDeviceType.SRIOV_PF].pop()
        vfs = [dev for dev in self.tracker.pci_devs
               if dev.dev_type == fields.PciDeviceType.SRIOV_VF]
        self.assertEqual(2, len(vfs))

        # Assert we build the device tree correctly
        self.assertEqual(vfs, pf.child_devices)
        for vf in vfs:
            self.assertEqual(vf.parent_device, pf)

    def test_pcidev_tracker_create_device_tree_pf_only(self):
        self._create_tracker([fake_db_dev_3])

        self.assertEqual(len(self.tracker.pci_devs), 1)
        free_devs = self.tracker.pci_stats.get_free_devs()
        self.assertEqual(len(free_devs), 1)
        self.assertEqual(list(self.tracker.stale), [])
        self.assertEqual(len(self.tracker.stats.pools), 1)
        self.assertEqual(self.tracker.node_id, 1)
        pf = self.tracker.pci_devs[0]
        self.assertIsNone(pf.parent_device)
        self.assertEqual([], pf.child_devices)

    def test_pcidev_tracker_create_device_tree_vf_only(self):
        self._create_tracker([fake_db_dev_4])

        self.assertEqual(len(self.tracker.pci_devs), 1)
        free_devs = self.tracker.pci_stats.get_free_devs()
        self.assertEqual(len(free_devs), 1)
        self.assertEqual(list(self.tracker.stale), [])
        self.assertEqual(len(self.tracker.stats.pools), 1)
        self.assertEqual(self.tracker.node_id, 1)
        vf = self.tracker.pci_devs[0]
        self.assertIsNone(vf.parent_device)
        self.assertEqual([], vf.child_devices)

    @mock.patch.object(zun.objects.PciDevice, 'list_by_compute_node')
    def test_pcidev_tracker_create_no_nodeid(self, mock_get_cn):
        self.tracker = manager.PciDevTracker(self.fake_context)
        self.assertEqual(len(self.tracker.pci_devs), 0)
        self.assertFalse(mock_get_cn.called)

    @mock.patch.object(zun.objects.PciDevice, 'list_by_compute_node')
    def test_pcidev_tracker_create_with_nodeid(self, mock_get_cn):
        self.tracker = manager.PciDevTracker(self.fake_context, node_id=1)
        mock_get_cn.assert_called_once_with(self.fake_context, 1)

    def test_set_hvdev_new_dev(self):
        fake_pci_3 = dict(fake_pci, address='0000:00:00.4', vendor_id='v2')
        fake_pci_devs = [copy.deepcopy(fake_pci), copy.deepcopy(fake_pci_1),
                         copy.deepcopy(fake_pci_2), copy.deepcopy(fake_pci_3)]
        self.tracker._set_hvdevs(fake_pci_devs)
        self.assertEqual(len(self.tracker.pci_devs), 4)
        self.assertEqual(set([dev.address for
                              dev in self.tracker.pci_devs]),
                         set(['0000:00:00.1', '0000:00:00.2',
                              '0000:00:00.3', '0000:00:00.4']))
        self.assertEqual(set([dev.vendor_id for
                              dev in self.tracker.pci_devs]),
                         set(['v', 'v1', 'v2']))

    def test_set_hvdev_new_dev_tree_maintained(self):
        # Make sure the device tree is properly maintained when there are new
        # devices reported by the driver
        self._create_tracker(fake_db_devs_tree)

        fake_new_device = dict(fake_pci_5, id=12, address='0000:00:02.3')
        fake_pci_devs = [copy.deepcopy(fake_pci_3),
                         copy.deepcopy(fake_pci_4),
                         copy.deepcopy(fake_pci_5),
                         copy.deepcopy(fake_new_device)]
        self.tracker._set_hvdevs(fake_pci_devs)
        self.assertEqual(len(self.tracker.pci_devs), 4)

        pf = [dev for dev in self.tracker.pci_devs
              if dev.dev_type == fields.PciDeviceType.SRIOV_PF].pop()
        vfs = [dev for dev in self.tracker.pci_devs
               if dev.dev_type == fields.PciDeviceType.SRIOV_VF]
        self.assertEqual(3, len(vfs))

        # Assert we build the device tree correctly
        self.assertEqual(vfs, pf.child_devices)
        for vf in vfs:
            self.assertEqual(vf.parent_device, pf)

    def test_set_hvdev_changed(self):
        fake_pci_v2 = dict(fake_pci, address='0000:00:00.2', vendor_id='v1')
        fake_pci_devs = [copy.deepcopy(fake_pci), copy.deepcopy(fake_pci_2),
                         copy.deepcopy(fake_pci_v2)]
        self.tracker._set_hvdevs(fake_pci_devs)
        self.assertEqual(set([dev.vendor_id for
                             dev in self.tracker.pci_devs]),
                         set(['v', 'v1']))

    def test_set_hvdev_remove(self):
        self.tracker._set_hvdevs([fake_pci])
        self.assertEqual(
            len([dev for dev in self.tracker.pci_devs
                 if dev.status == fields.PciDeviceStatus.REMOVED]),
            2)

    def test_set_hvdev_remove_tree_maintained(self):
        # Make sure the device tree is properly maintained when there are
        # devices removed from the system (not reported by the driver but known
        # from previous scans)
        self._create_tracker(fake_db_devs_tree)

        fake_pci_devs = [copy.deepcopy(fake_pci_3), copy.deepcopy(fake_pci_4)]
        self.tracker._set_hvdevs(fake_pci_devs)
        self.assertEqual(
            2,
            len([dev for dev in self.tracker.pci_devs
                 if dev.status != fields.PciDeviceStatus.REMOVED]))
        pf = [dev for dev in self.tracker.pci_devs
              if dev.dev_type == fields.PciDeviceType.SRIOV_PF].pop()
        vfs = [dev for dev in self.tracker.pci_devs
               if (dev.dev_type == fields.PciDeviceType.SRIOV_VF and
                   dev.status != fields.PciDeviceStatus.REMOVED)]
        self.assertEqual(1, len(vfs))

        self.assertEqual(vfs, pf.child_devices)
        self.assertEqual(vfs[0].parent_device, pf)

    def test_save(self):
        self.stub_out('zun.db.api.update_pci_device',
                      self._fake_pci_device_update)
        fake_pci_v3 = dict(fake_pci, address='0000:00:00.2', vendor_id='v3')
        fake_pci_devs = [copy.deepcopy(fake_pci), copy.deepcopy(fake_pci_2),
                         copy.deepcopy(fake_pci_v3)]
        self.tracker._set_hvdevs(fake_pci_devs)
        self.update_called = 0
        self.tracker.save()
        self.assertEqual(self.update_called, 3)

    def test_save_removed(self):
        self.stub_out('zun.db.api.update_pci_device',
                      self._fake_pci_device_update)
        self.stub_out('zun.db.api.destroy_pci_device',
                      self._fake_pci_device_destroy)
        self.assertEqual(len(self.tracker.pci_devs), 3)
        dev = self.tracker.pci_devs[0]
        self.destroy_called = 0
        self.update_called = 0
        dev.remove()
        self.tracker.save()
        self.assertEqual(len(self.tracker.pci_devs), 2)
        self.assertEqual(self.destroy_called, 1)
