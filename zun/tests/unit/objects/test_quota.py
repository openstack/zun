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

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestQuotaObject(base.DbTestCase):

    def setUp(self):
        super(TestQuotaObject, self).setUp()
        self.fake_quota = utils.get_test_quota()

    def test_get_quota(self):
        project_id = self.fake_quota['project_id']
        resource = self.fake_quota['resource']
        with mock.patch.object(self.dbapi, 'quota_get',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_quota
            quota = objects.Quota.get(self.context, project_id, resource)
            mock_get.assert_called_once_with(
                self.context, project_id, resource)
            self.assertEqual(self.context, quota._context)

    def test_get_all_quotas_by_project(self):
        project_id = self.fake_quota['project_id']
        with mock.patch.object(self.dbapi, 'quota_get_all_by_project',
                               autospec=True) as mock_get_all:
            mock_get_all.return_value = {
                'project_id': project_id,
                'resource_1': 10,
                'resource_2': 20
            }
            quotas_dict = objects.Quota.get_all(self.context, project_id)
            mock_get_all.assert_called_once_with(self.context, project_id)
            self.assertEqual(project_id, quotas_dict['project_id'])

    def test_create_quota(self):
        project_id = self.fake_quota['project_id']
        resource = self.fake_quota['resource']
        hard_limit = self.fake_quota['hard_limit']
        with mock.patch.object(self.dbapi, 'quota_create',
                               autospec=True) as mock_create:
            mock_create.return_value = self.fake_quota
            quota = objects.Quota(
                self.context, **utils.get_test_quota_value())
            quota.create(self.context)
            mock_create.assert_called_once_with(
                self.context, project_id, resource, hard_limit)

    def test_destroy_quota(self):
        project_id = self.fake_quota['project_id']
        resource = self.fake_quota['resource']
        with mock.patch.object(self.dbapi, 'quota_get',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_quota
            with mock.patch.object(self.dbapi, 'quota_destroy',
                                   autospec=True) as mock_destroy:
                quota = objects.Quota.get(self.context, project_id,
                                          resource)
                quota.destroy()
                mock_destroy.assert_called_once_with(
                    None, project_id, resource)
                self.assertEqual(self.context, quota._context)

    def test_update_quota(self):
        project_id = self.fake_quota['project_id']
        resource = self.fake_quota['resource']
        with mock.patch.object(self.dbapi, 'quota_get',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_quota
            with mock.patch.object(self.dbapi, 'quota_update',
                                   autospec=True) as mock_update:
                quota = objects.Quota.get(self.context, project_id,
                                          resource)
                quota.hard_limit = 100
                quota.update()

                mock_get.assert_called_once_with(self.context, project_id,
                                                 resource)
                mock_update.assert_called_once_with(
                    None, project_id, resource, 100)
                self.assertEqual(self.context, quota._context)
                self.assertEqual(100, quota.hard_limit)
