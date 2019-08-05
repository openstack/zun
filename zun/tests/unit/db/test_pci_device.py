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

"""Tests for manipulating pci device via the DB API"""

from zun.common import context
from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.objects import fields as z_fields
from zun.tests.unit.db import base
from zun.tests import uuidsentinel

CONF = zun.conf.CONF


class DbPciDeviceTestCase(base.DbTestCase, base.ModelsObjectComparatorMixin):

    def setUp(self):
        super(DbPciDeviceTestCase, self).setUp()
        self.admin_context = context.get_admin_context()
        self._compute_node = None
        self.ignored_keys = ['id', 'updated_at', 'created_at']

    def _get_fake_pci_devs(self):
        v1 = {'id': 3353,
              'uuid': uuidsentinel.pci_device1,
              'compute_node_uuid': uuidsentinel.compute_node,
              'address': '0000:0f:08.7',
              'vendor_id': '8086',
              'product_id': '1520',
              'numa_node': 1,
              'dev_type': z_fields.PciDeviceType.SRIOV_VF,
              'dev_id': 'pci_0000:0f:08.7',
              'extra_info': '{}',
              'label': 'label_8086_1520',
              'status': z_fields.PciDeviceStatus.AVAILABLE,
              'container_uuid': '00000000-0000-0000-0000-000000000010',
              'request_id': None,
              'parent_addr': '0000:0f:00.1'}
        v2 = {'id': 3356,
              'uuid': uuidsentinel.pci_device3356,
              'compute_node_uuid': uuidsentinel.compute_node,
              'address': '0000:0f:03.7',
              'parent_addr': '0000:0f:03.0',
              'vendor_id': '8083',
              'product_id': '1523',
              'numa_node': 0,
              'dev_type': z_fields.PciDeviceType.SRIOV_VF,
              'dev_id': 'pci_0000:0f:08.7',
              'extra_info': '{}',
              'label': 'label_8086_1520',
              'status': z_fields.PciDeviceStatus.AVAILABLE,
              'container_uuid': '00000000-0000-0000-0000-000000000010',
              'request_id': None}
        return v1, v2

    @property
    def compute_node(self):
        if self._compute_node is None:
            self._compute_node = dbapi.create_compute_node(
                self.admin_context,
                {'uuid': uuidsentinel.compute_node,
                 'rp_uuid': uuidsentinel.compute_node,
                 'hostname': 'fake_compute_node',
                 'mem_total': 40960,
                 'mem_free': 20480,
                 'mem_available': 20480,
                 'mem_used': 20480,
                 'total_containers': 0,
                 'running_containers': 0,
                 'paused_containers': 0,
                 'stopped_containers': 0,
                 'cpus': 48,
                 'cpu_used': 24})
        return self._compute_node

    def _create_fake_pci_devs(self):
        v1, v2 = self._get_fake_pci_devs()
        for i in v1, v2:
            i['compute_node_uuid'] = self.compute_node['uuid']

        dbapi.update_pci_device(v1['compute_node_uuid'],
                                v1['address'], v1)
        dbapi.update_pci_device(v2['compute_node_uuid'],
                                v2['address'], v2)

        return (v1, v2)

    def test_get_pci_device_by_addr(self):
        v1, v2 = self._create_fake_pci_devs()
        result = dbapi.get_pci_device_by_addr(self.compute_node['uuid'],
                                              '0000:0f:08.7')
        self._assertEqualObjects(v1, result, self.ignored_keys)

    def test_get_pci_device_by_addr_not_found(self):
        self._create_fake_pci_devs()
        self.assertRaises(exception.PciDeviceNotFound,
                          dbapi.get_pci_device_by_addr,
                          uuidsentinel.compute_node, '0000:0f:08:09')

    def test_get_all_pci_device_by_parent_addr(self):
        v1, v2 = self._create_fake_pci_devs()
        results = dbapi.get_all_pci_device_by_parent_addr(
            uuidsentinel.compute_node, '0000:0f:00.1')
        self._assertEqualListsOfObjects([v1], results, self.ignored_keys)

    def test_get_all_pci_device_by_parent_addr_empty(self):
        v1, v2 = self._create_fake_pci_devs()
        results = dbapi.get_all_pci_device_by_parent_addr(
            uuidsentinel.compute_node, '0000:0f:01.6')
        self.assertEqual(len(results), 0)

    def test_get_pci_device_by_id(self):
        v1, v2 = self._create_fake_pci_devs()
        result = dbapi.get_pci_device_by_id(3353)
        self._assertEqualObjects(v1, result, self.ignored_keys)

    def test_get_pci_device_by_id_not_found(self):
        self._create_fake_pci_devs()
        self.assertRaises(exception.PciDeviceNotFoundById,
                          dbapi.get_pci_device_by_id, 3354)

    def test_get_all_pci_device_by_node(self):
        v1, v2 = self._create_fake_pci_devs()
        results = dbapi.get_all_pci_device_by_node(uuidsentinel.compute_node)
        self._assertEqualListsOfObjects(results, [v1, v2], self.ignored_keys)

    def test_get_all_pci_device_by_node_empty(self):
        v1, v2 = self._get_fake_pci_devs()
        results = dbapi.get_all_pci_device_by_node(9)
        self.assertEqual(len(results), 0)

    def test_get_pci_device_by_container_uuid(self):
        v1, v2 = self._create_fake_pci_devs()
        v1['status'] = z_fields.PciDeviceStatus.ALLOCATED
        v2['status'] = z_fields.PciDeviceStatus.ALLOCATED
        dbapi.update_pci_device(v1['compute_node_uuid'],
                                v1['address'], v1)
        dbapi.update_pci_device(v2['compute_node_uuid'],
                                v2['address'], v2)
        results = dbapi.get_all_pci_device_by_container_uuid(
            '00000000-0000-0000-0000-000000000010')
        self._assertEqualListsOfObjects(results, [v1, v2], self.ignored_keys)

    def test_get_pci_device_by_container_uuid_check_status(self):
        v1, v2 = self._create_fake_pci_devs()
        v1['status'] = z_fields.PciDeviceStatus.ALLOCATED
        v2['status'] = z_fields.PciDeviceStatus.CLAIMED
        dbapi.update_pci_device(v1['compute_node_uuid'],
                                v1['address'], v1)
        dbapi.update_pci_device(v2['compute_node_uuid'],
                                v2['address'], v2)
        results = dbapi.get_all_pci_device_by_container_uuid(
            '00000000-0000-0000-0000-000000000010')
        self._assertEqualListsOfObjects(results, [v1], self.ignored_keys)

    def test_update_pci_device(self):
        v1, v2 = self._create_fake_pci_devs()
        v1['status'] = z_fields.PciDeviceStatus.ALLOCATED
        dbapi.update_pci_device(v1['compute_node_uuid'],
                                v1['address'], v1)
        result = dbapi.get_pci_device_by_addr(uuidsentinel.compute_node,
                                              '0000:0f:08.7')
        self._assertEqualObjects(v1, result, self.ignored_keys)

        v1['status'] = z_fields.PciDeviceStatus.CLAIMED
        dbapi.update_pci_device(v1['compute_node_uuid'],
                                v1['address'], v1)
        result = dbapi.get_pci_device_by_addr(uuidsentinel.compute_node,
                                              '0000:0f:08.7')
        self._assertEqualObjects(v1, result, self.ignored_keys)

    def test_destroy_pci_device(self):
        v1, v2 = self._create_fake_pci_devs()
        results = dbapi.get_all_pci_device_by_node(self.compute_node['uuid'])
        self._assertEqualListsOfObjects(results, [v1, v2], self.ignored_keys)
        dbapi.destroy_pci_device(v1['compute_node_uuid'], v1['address'])
        results = dbapi.get_all_pci_device_by_node(self.compute_node['uuid'])
        self._assertEqualListsOfObjects(results, [v2], self.ignored_keys)

    def test_destroy_pci_device_exception(self):
        v1, v2 = self._get_fake_pci_devs()
        self.assertRaises(exception.PciDeviceNotFound,
                          dbapi.destroy_pci_device,
                          v1['compute_node_uuid'],
                          v1['address'])
