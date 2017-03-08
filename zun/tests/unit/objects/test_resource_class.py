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

from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestResourceClassObject(base.DbTestCase):

    def setUp(self):
        super(TestResourceClassObject, self).setUp()
        self.fake_resource = utils.get_test_resource_class()

    def test_get_by_name(self):
        name = self.fake_resource['name']
        with mock.patch.object(self.dbapi, 'get_resource_class',
                               autospec=True) as mock_get_resource_class:
            mock_get_resource_class.return_value = self.fake_resource
            resource = objects.ResourceClass.get_by_name(self.context, name)
            mock_get_resource_class.assert_called_once_with(
                self.context, name)
            self.assertEqual(self.context, resource._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_resource_classes',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_resource]
            resources = objects.ResourceClass.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(resources, HasLength(1))
            self.assertIsInstance(resources[0], objects.ResourceClass)
            self.assertEqual(self.context, resources[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_resource_class',
                               autospec=True) as mock_create:
            mock_create.return_value = self.fake_resource
            resource = objects.ResourceClass(
                self.context, **self.fake_resource)
            resource.create(self.context)
            mock_create.assert_called_once_with(
                self.context, self.fake_resource)
            self.assertEqual(self.context, resource._context)

    def test_destroy(self):
        rc_uuid = self.fake_resource['uuid']
        with mock.patch.object(self.dbapi, 'get_resource_class',
                               autospec=True) as mock_get_resource_class:
            mock_get_resource_class.return_value = self.fake_resource
            with mock.patch.object(self.dbapi, 'destroy_resource_class',
                                   autospec=True) as mock_destroy:
                resource = objects.ResourceClass.get_by_uuid(
                    self.context, rc_uuid)
                resource.destroy()
                mock_get_resource_class.assert_called_once_with(
                    self.context, rc_uuid)
                mock_destroy.assert_called_once_with(None, rc_uuid)
                self.assertEqual(self.context, resource._context)

    def test_save(self):
        rc_uuid = self.fake_resource['uuid']
        with mock.patch.object(self.dbapi, 'get_resource_class',
                               autospec=True) as mock_get_resource_class:
            mock_get_resource_class.return_value = self.fake_resource
            with mock.patch.object(self.dbapi, 'update_resource_class',
                                   autospec=True) as mock_update:
                resource = objects.ResourceClass.get_by_uuid(
                    self.context, rc_uuid)
                resource.name = 'MEMORY_MB'
                resource.save()

                mock_get_resource_class.assert_called_once_with(
                    self.context, rc_uuid)
                mock_update.assert_called_once_with(
                    None, rc_uuid,
                    {'name': 'MEMORY_MB'})
                self.assertEqual(self.context, resource._context)

    def test_refresh(self):
        rc_uuid = self.fake_resource['uuid']
        name = self.fake_resource['name']
        new_name = 'MEMORY_MB'
        returns = [dict(self.fake_resource, name=name),
                   dict(self.fake_resource, name=new_name)]
        expected = [mock.call(self.context, rc_uuid),
                    mock.call(self.context, rc_uuid)]
        with mock.patch.object(self.dbapi, 'get_resource_class',
                               side_effect=returns,
                               autospec=True) as mock_get_resource_class:
            resource = objects.ResourceClass.get_by_uuid(
                self.context, rc_uuid)
            self.assertEqual(name, resource.name)
            resource.refresh()
            self.assertEqual(new_name, resource.name)
            self.assertEqual(
                expected, mock_get_resource_class.call_args_list)
            self.assertEqual(self.context, resource._context)
