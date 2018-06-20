# Copyright 2015 OpenStack Foundation
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

from oslo_utils import uuidutils
from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestContainerObject(base.DbTestCase):

    def setUp(self):
        super(TestContainerObject, self).setUp()
        self.fake_container = utils.get_test_container()

    def test_get_by_uuid(self):
        uuid = self.fake_container['uuid']
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            container = objects.Container.get_by_uuid(self.context, uuid)
            mock_get_container.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, container._context)

    def test_get_by_name(self):
        name = self.fake_container['name']
        with mock.patch.object(self.dbapi, 'get_container_by_name',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            container = objects.Container.get_by_name(self.context, name)
            mock_get_container.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, container._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_containers',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_container]
            containers = objects.Container.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(containers, HasLength(1))
            self.assertIsInstance(containers[0], objects.Container)
            self.assertEqual(self.context, containers[0]._context)

    def test_list_by_host(self):
        with mock.patch.object(self.dbapi, 'list_containers',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_container]
            containers = objects.Container.list_by_host(self.context,
                                                        'test_host')
            mock_get_list.assert_called_once_with(
                self.context, {'host': 'test_host'}, None, None, None, None)
            self.assertThat(containers, HasLength(1))
            self.assertIsInstance(containers[0], objects.Container)
            self.assertEqual(self.context, containers[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_containers',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_container]
            filt = {'status': 'Running'}
            containers = objects.Container.list(self.context,
                                                filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(containers, HasLength(1))
            self.assertIsInstance(containers[0], objects.Container)
            self.assertEqual(self.context, containers[0]._context)
            mock_get_list.assert_called_once_with(self.context,
                                                  filters=filt,
                                                  limit=None, marker=None,
                                                  sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_container',
                               autospec=True) as mock_create_container:
            mock_create_container.return_value = self.fake_container
            container = objects.Container(self.context, **self.fake_container)
            container.create(self.context)
            mock_create_container.assert_called_once_with(self.context,
                                                          self.fake_container)
            self.assertEqual(self.context, container._context)

    def test_status_reason_in_fields(self):
        with mock.patch.object(self.dbapi, 'create_container',
                               autospec=True) as mock_create_container:
            mock_create_container.return_value = self.fake_container
            container = objects.Container(self.context, **self.fake_container)
            self.assertTrue(hasattr(container, 'status_reason'))
            container.status_reason = "Docker Error happened"
            container.create(self.context)
            self.assertEqual(
                "Docker Error happened",
                mock_create_container.call_args_list[0][0][1]['status_reason'])

    def test_destroy(self):
        uuid = self.fake_container['uuid']
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            with mock.patch.object(self.dbapi, 'destroy_container',
                                   autospec=True) as mock_destroy_container:
                container = objects.Container.get_by_uuid(self.context, uuid)
                container.destroy()
                mock_get_container.assert_called_once_with(self.context, uuid)
                mock_destroy_container.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, container._context)

    def test_save(self):
        uuid = self.fake_container['uuid']
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            with mock.patch.object(self.dbapi, 'update_container',
                                   autospec=True) as mock_update_container:
                container = objects.Container.get_by_uuid(self.context, uuid)
                container.image = 'container.img'
                container.memory = '512m'
                container.environment = {"key1": "val", "key2": "val2"}
                container.save()

                mock_get_container.assert_called_once_with(self.context, uuid)
                mock_update_container.assert_called_once_with(
                    None, uuid,
                    {'image': 'container.img',
                     'environment': {"key1": "val", "key2": "val2"},
                     'memory': '512m'})
                self.assertEqual(self.context, container._context)

    def test_refresh(self):
        uuid = self.fake_container['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_container, uuid=uuid),
                   dict(self.fake_container, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_container:
            container = objects.Container.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, container.uuid)
            container.refresh()
            self.assertEqual(new_uuid, container.uuid)
            self.assertEqual(expected, mock_get_container.call_args_list)
            self.assertEqual(self.context, container._context)

    @mock.patch('zun.objects.PciDevice.list_by_container_uuid')
    def test_obj_load_attr_pci_devices(self, mock_list):
        uuid = self.fake_container['uuid']
        dev_dict = {'dev_id': 'fake_dev_id',
                    'container_uuid': 'fake_container_uuid'}
        pci_devices = [objects.PciDevice.create(self.context, dev_dict)]
        mock_list.return_value = pci_devices
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            container = objects.Container.get_by_uuid(self.context, uuid)
            container.obj_load_attr('pci_devices')
            self.assertEqual(pci_devices, container.pci_devices)

    @mock.patch('zun.objects.ExecInstance.list_by_container_id')
    def test_obj_load_attr_exec_instances(self, mock_list):
        uuid = self.fake_container['uuid']
        exec_dict = {'exec_id': 'fake_exec_id',
                     'container_id': self.fake_container['id']}
        exec_inst = objects.ExecInstance(self.context, **exec_dict)
        exec_inst.create(self.context)
        exec_insts = [exec_inst]
        mock_list.return_value = exec_insts
        with mock.patch.object(self.dbapi, 'get_container_by_uuid',
                               autospec=True) as mock_get_container:
            mock_get_container.return_value = self.fake_container
            container = objects.Container.get_by_uuid(self.context, uuid)
            container.obj_load_attr('exec_instances')
            self.assertEqual(exec_insts, container.exec_instances)
