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


class TestVolumeMappingObject(base.DbTestCase):

    def setUp(self):
        super(TestVolumeMappingObject, self).setUp()
        self.fake_volume_mapping = utils.get_test_volume_mapping()

    def test_get_by_uuid(self):
        uuid = self.fake_volume_mapping['uuid']
        with mock.patch.object(self.dbapi, 'get_volume_mapping_by_uuid',
                               autospec=True) as mock_get_volume_mapping:
            mock_get_volume_mapping.return_value = self.fake_volume_mapping
            volume_mapping = objects.VolumeMapping.get_by_uuid(self.context,
                                                               uuid)
            mock_get_volume_mapping.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, volume_mapping._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_volume_mappings',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_volume_mapping]
            volume_mappings = objects.VolumeMapping.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(volume_mappings, HasLength(1))
            self.assertIsInstance(volume_mappings[0], objects.VolumeMapping)
            self.assertEqual(self.context, volume_mappings[0]._context)

    def test_list_by_container(self):
        with mock.patch.object(self.dbapi, 'list_volume_mappings',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_volume_mapping]
            volume_mappings = objects.VolumeMapping.list_by_container(
                self.context, 'fake_container_uuid')
            mock_get_list.assert_called_once_with(
                self.context, {'container_uuid': 'fake_container_uuid'},
                None, None, None, None)
            self.assertThat(volume_mappings, HasLength(1))
            self.assertIsInstance(volume_mappings[0], objects.VolumeMapping)
            self.assertEqual(self.context, volume_mappings[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_volume_mappings',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_volume_mapping]
            filt = {'volume_provider': 'fake_provider'}
            volume_mappings = objects.VolumeMapping.list(self.context,
                                                         filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(volume_mappings, HasLength(1))
            self.assertIsInstance(volume_mappings[0], objects.VolumeMapping)
            self.assertEqual(self.context, volume_mappings[0]._context)
            mock_get_list.assert_called_once_with(self.context,
                                                  filters=filt,
                                                  limit=None, marker=None,
                                                  sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_volume_mapping',
                               autospec=True) as mock_create_volume_mapping:
            mock_create_volume_mapping.return_value = self.fake_volume_mapping
            volume_mapping_dict = dict(self.fake_volume_mapping)
            del volume_mapping_dict['id']
            volume_mapping = objects.VolumeMapping(self.context,
                                                   **volume_mapping_dict)
            volume_mapping.create(self.context)
            mock_create_volume_mapping.assert_called_once_with(
                self.context, volume_mapping_dict)
            self.assertEqual(self.context, volume_mapping._context)

    def test_destroy(self):
        uuid = self.fake_volume_mapping['uuid']
        with mock.patch.object(self.dbapi, 'get_volume_mapping_by_uuid',
                               autospec=True) as mock_get_volume_mapping:
            mock_get_volume_mapping.return_value = self.fake_volume_mapping
            with mock.patch.object(self.dbapi, 'destroy_volume_mapping',
                                   autospec=True
                                   ) as mock_destroy_volume_mapping:
                volume_mapping = objects.VolumeMapping.get_by_uuid(
                    self.context, uuid)
                volume_mapping.destroy()
                mock_get_volume_mapping.assert_called_once_with(self.context,
                                                                uuid)
                mock_destroy_volume_mapping.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, volume_mapping._context)

    def test_save(self):
        uuid = self.fake_volume_mapping['uuid']
        with mock.patch.object(self.dbapi, 'get_volume_mapping_by_uuid',
                               autospec=True) as mock_get_volume_mapping:
            mock_get_volume_mapping.return_value = self.fake_volume_mapping
            with mock.patch.object(self.dbapi, 'update_volume_mapping',
                                   autospec=True
                                   ) as mock_update_volume_mapping:
                volume_mapping = objects.VolumeMapping.get_by_uuid(
                    self.context, uuid)
                volume_mapping.connection_info = 'new_info'
                volume_mapping.save()

                mock_get_volume_mapping.assert_called_once_with(self.context,
                                                                uuid)
                mock_update_volume_mapping.assert_called_once_with(
                    None, uuid, {'connection_info': 'new_info'})
                self.assertEqual(self.context, volume_mapping._context)

    def test_refresh(self):
        uuid = self.fake_volume_mapping['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_volume_mapping, uuid=uuid),
                   dict(self.fake_volume_mapping, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_volume_mapping_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_volume_mapping:
            volume_mapping = objects.VolumeMapping.get_by_uuid(self.context,
                                                               uuid)
            self.assertEqual(uuid, volume_mapping.uuid)
            volume_mapping.refresh()
            self.assertEqual(new_uuid, volume_mapping.uuid)
            self.assertEqual(expected, mock_get_volume_mapping.call_args_list)
            self.assertEqual(self.context, volume_mapping._context)
