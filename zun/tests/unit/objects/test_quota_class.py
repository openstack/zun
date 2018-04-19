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

from zun.common import consts
from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestQuotaClassObject(base.DbTestCase):

    def setUp(self):
        super(TestQuotaClassObject, self).setUp()
        self.fake_quota_class = utils.get_test_quota_class()

    def test_get_quota_class(self):
        class_name = self.fake_quota_class['class_name']
        resource = self.fake_quota_class['resource']
        with mock.patch.object(self.dbapi, 'quota_class_get',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_quota_class
            quota_class = objects.QuotaClass.get(
                self.context, class_name, resource)
            mock_get.assert_called_once_with(
                self.context, class_name, resource)
            self.assertEqual(self.context, quota_class._context)

    def test_get_all_with_default(self):
        class_name = consts.DEFAULT_QUOTA_CLASS_NAME
        with mock.patch.object(self.dbapi, 'quota_class_get_default',
                               autospec=True) as mock_get_all:
            mock_get_all.return_value = {
                'class_name': class_name,
                'resource_1': 10,
                'resource_2': 20
            }
            quota_class_dict = objects.QuotaClass.get_all(self.context)
            mock_get_all.assert_called_once_with(self.context)
            self.assertEqual(class_name, quota_class_dict['class_name'])

    def test_get_all_with_class_name(self):
        class_name = self.fake_quota_class['class_name']
        with mock.patch.object(self.dbapi, 'quota_class_get_all_by_name',
                               autospec=True) as mock_get_all:
            mock_get_all.return_value = {
                'class_name': class_name,
                'resource_1': 10,
                'resource_2': 20
            }
            quota_class_dict = objects.QuotaClass.get_all(
                self.context, class_name)
            mock_get_all.assert_called_once_with(self.context, class_name)
            self.assertEqual(class_name, quota_class_dict['class_name'])

    def test_create_quota_class(self):
        class_name = self.fake_quota_class['class_name']
        resource = self.fake_quota_class['resource']
        hard_limit = self.fake_quota_class['hard_limit']
        with mock.patch.object(self.dbapi, 'quota_class_create',
                               autospec=True) as mock_create:
            mock_create.return_value = self.fake_quota_class
            quota_class = objects.QuotaClass(
                self.context, **utils.get_test_quota_class_value())
            quota_class.create(self.context)
            mock_create.assert_called_once_with(
                self.context, class_name, resource, hard_limit)

    def test_update_quota(self):
        class_name = self.fake_quota_class['class_name']
        resource = self.fake_quota_class['resource']
        with mock.patch.object(self.dbapi, 'quota_class_get',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_quota_class
            with mock.patch.object(self.dbapi, 'quota_class_update',
                                   autospec=True) as mock_update:
                quota_class = objects.QuotaClass.get(
                    self.context, class_name, resource)
                quota_class.hard_limit = 100
                quota_class.update()

                mock_get.assert_called_once_with(
                    self.context, class_name, resource)
                mock_update.assert_called_once_with(
                    None, class_name, resource, 100)
                self.assertEqual(self.context, quota_class._context)
                self.assertEqual(100, quota_class.hard_limit)
