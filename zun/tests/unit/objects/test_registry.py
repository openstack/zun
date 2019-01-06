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

from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestRegistryObject(base.DbTestCase):

    def setUp(self):
        super(TestRegistryObject, self).setUp()
        self.fake_cpuset = utils.get_cpuset_dict()
        self.fake_registry = utils.get_test_registry(
            cpuset=self.fake_cpuset, cpu_policy='dedicated')

    def test_get_by_uuid(self):
        uuid = self.fake_registry['uuid']
        with mock.patch.object(self.dbapi, 'get_registry_by_uuid',
                               autospec=True) as mock_get_registry:
            mock_get_registry.return_value = self.fake_registry
            registry = objects.Registry.get_by_uuid(self.context, uuid)
            mock_get_registry.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, registry._context)

    def test_get_by_name(self):
        name = self.fake_registry['name']
        with mock.patch.object(self.dbapi, 'get_registry_by_name',
                               autospec=True) as mock_get_registry:
            mock_get_registry.return_value = self.fake_registry
            registry = objects.Registry.get_by_name(self.context, name)
            mock_get_registry.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, registry._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_registries',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_registry]
            registries = objects.Registry.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(registries, HasLength(1))
            self.assertIsInstance(registries[0], objects.Registry)
            self.assertEqual(self.context, registries[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_registries',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_registry]
            filt = {'username': 'fake_username'}
            registries = objects.Registry.list(self.context,
                                               filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(registries, HasLength(1))
            self.assertIsInstance(registries[0], objects.Registry)
            self.assertEqual(self.context, registries[0]._context)
            mock_get_list.assert_called_once_with(self.context,
                                                  filters=filt,
                                                  limit=None, marker=None,
                                                  sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_registry',
                               autospec=True) as mock_create_registry:
            mock_create_registry.return_value = self.fake_registry
            registry_dict = dict(self.fake_registry)
            registry = objects.Registry(self.context, **registry_dict)
            registry.create(self.context)
            mock_create_registry.assert_called_once_with(self.context,
                                                         self.fake_registry)
            self.assertEqual(self.context, registry._context)

    def test_destroy(self):
        uuid = self.fake_registry['uuid']
        with mock.patch.object(self.dbapi, 'get_registry_by_uuid',
                               autospec=True) as mock_get_registry:
            mock_get_registry.return_value = self.fake_registry
            with mock.patch.object(self.dbapi, 'destroy_registry',
                                   autospec=True) as mock_destroy_registry:
                registry = objects.Registry.get_by_uuid(self.context, uuid)
                registry.destroy()
                mock_get_registry.assert_called_once_with(self.context, uuid)
                mock_destroy_registry.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, registry._context)

    def test_save(self):
        uuid = self.fake_registry['uuid']
        with mock.patch.object(self.dbapi, 'get_registry_by_uuid',
                               autospec=True) as mock_get_registry:
            mock_get_registry.return_value = self.fake_registry
            with mock.patch.object(self.dbapi, 'update_registry',
                                   autospec=True) as mock_update_registry:
                registry = objects.Registry.get_by_uuid(self.context, uuid)
                registry.domain = 'testdomain.io'
                registry.username = 'testuesrname'
                registry.password = 'testpassword'
                registry.name = 'testname'
                registry.save()

                mock_get_registry.assert_called_once_with(self.context, uuid)
                mock_update_registry.assert_called_once_with(
                    None, uuid,
                    {'domain': 'testdomain.io',
                     'username': 'testuesrname',
                     'password': 'testpassword',
                     'name': 'testname'})
                self.assertEqual(self.context, registry._context)
