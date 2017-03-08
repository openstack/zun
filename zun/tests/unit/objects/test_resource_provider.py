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


class TestResourceProviderObject(base.DbTestCase):

    def setUp(self):
        super(TestResourceProviderObject, self).setUp()
        self.fake_provider = utils.get_test_resource_provider()

    def test_get_by_uuid(self):
        uuid = self.fake_provider['uuid']
        with mock.patch.object(self.dbapi, 'get_resource_provider',
                               autospec=True) as mock_get_resource_provider:
            mock_get_resource_provider.return_value = self.fake_provider
            provider = objects.ResourceProvider.get_by_uuid(self.context, uuid)
            mock_get_resource_provider.assert_called_once_with(
                self.context, uuid)
            self.assertEqual(self.context, provider._context)

    def test_get_by_name(self):
        name = self.fake_provider['name']
        with mock.patch.object(self.dbapi, 'get_resource_provider',
                               autospec=True) as mock_get_resource_provider:
            mock_get_resource_provider.return_value = self.fake_provider
            provider = objects.ResourceProvider.get_by_name(self.context, name)
            mock_get_resource_provider.assert_called_once_with(
                self.context, name)
            self.assertEqual(self.context, provider._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_resource_providers',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_provider]
            providers = objects.ResourceProvider.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(providers, HasLength(1))
            self.assertIsInstance(providers[0], objects.ResourceProvider)
            self.assertEqual(self.context, providers[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_resource_providers',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_provider]
            filt = {'name': 'testprovider'}
            providers = objects.ResourceProvider.list(
                self.context, filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(providers, HasLength(1))
            self.assertIsInstance(providers[0], objects.ResourceProvider)
            self.assertEqual(self.context, providers[0]._context)
            mock_get_list.assert_called_once_with(
                self.context, filters=filt, limit=None, marker=None,
                sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_resource_provider',
                               autospec=True) as mock_create:
            mock_create.return_value = self.fake_provider
            provider = objects.ResourceProvider(
                self.context, **self.fake_provider)
            provider.create(self.context)
            mock_create.assert_called_once_with(
                self.context, self.fake_provider)
            self.assertEqual(self.context, provider._context)

    def test_destroy(self):
        uuid = self.fake_provider['uuid']
        with mock.patch.object(self.dbapi, 'get_resource_provider',
                               autospec=True) as mock_get_resource_provider:
            mock_get_resource_provider.return_value = self.fake_provider
            with mock.patch.object(self.dbapi, 'destroy_resource_provider',
                                   autospec=True) as mock_destroy:
                provider = objects.ResourceProvider.get_by_uuid(
                    self.context, uuid)
                provider.destroy()
                mock_get_resource_provider.assert_called_once_with(
                    self.context, uuid)
                mock_destroy.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, provider._context)

    def test_save(self):
        uuid = self.fake_provider['uuid']
        with mock.patch.object(self.dbapi, 'get_resource_provider',
                               autospec=True) as mock_get_resource_provider:
            mock_get_resource_provider.return_value = self.fake_provider
            with mock.patch.object(self.dbapi, 'update_resource_provider',
                                   autospec=True) as mock_update:
                provider = objects.ResourceProvider.get_by_uuid(
                    self.context, uuid)
                provider.name = 'provider2'
                provider.root_provider = '09d0fcb9-155e-434a-ad76-3620b6382a37'
                provider.save()

                mock_get_resource_provider.assert_called_once_with(
                    self.context, uuid)
                mock_update.assert_called_once_with(
                    None, uuid,
                    {'name': 'provider2',
                     'root_provider': '09d0fcb9-155e-434a-ad76-3620b6382a37'})
                self.assertEqual(self.context, provider._context)

    def test_refresh(self):
        uuid = self.fake_provider['uuid']
        new_uuid = uuidutils.generate_uuid()
        returns = [dict(self.fake_provider, uuid=uuid),
                   dict(self.fake_provider, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_resource_provider',
                               side_effect=returns,
                               autospec=True) as mock_get_resource_provider:
            provider = objects.ResourceProvider.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, provider.uuid)
            provider.refresh()
            self.assertEqual(new_uuid, provider.uuid)
            self.assertEqual(
                expected, mock_get_resource_provider.call_args_list)
            self.assertEqual(self.context, provider._context)
