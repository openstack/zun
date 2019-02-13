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

"""Tests for manipulating Quota via the DB API"""

from zun.common import context
from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DBQuotaTestCase(base.DbTestCase):

    def setUp(self):
        super(DBQuotaTestCase, self).setUp()
        self.ctx = context.get_admin_context()
        self.project_id = 'fake_project_id'
        self.resource = 'containers'
        self.limit = 100

    def test_create_quota(self):
        quota = utils.create_test_quota(context=self.ctx,
                                        project_id=self.project_id,
                                        resource=self.resource,
                                        limit=self.limit)
        self.assertEqual(quota.project_id, self.project_id)
        self.assertEqual(quota.resource, self.resource)
        self.assertEqual(quota.hard_limit, self.limit)

    def test_get_quota(self):
        quota = utils.create_test_quota(context=self.ctx,
                                        project_id=self.project_id,
                                        resource=self.resource,
                                        limit=self.limit)
        res = dbapi.quota_get(context=self.ctx,
                              project_id=quota.project_id,
                              resource=quota.resource)
        self.assertEqual(quota.project_id, res.project_id)
        self.assertEqual(quota.resource, res.resource)
        self.assertEqual(quota.hard_limit, res.hard_limit)

    def test_get_all_project_quota(self):
        quota_1 = utils.create_test_quota(context=self.ctx,
                                          project_id=self.project_id,
                                          resource='resource_1',
                                          limit=10)
        quota_2 = utils.create_test_quota(context=self.ctx,
                                          project_id=self.project_id,
                                          resource='resource_2',
                                          limit=20)
        quotas = dbapi.quota_get_all_by_project(self.ctx, self.project_id)
        self.assertEqual(quotas['project_id'], self.project_id)
        self.assertEqual(quotas[quota_1.resource], quota_1.hard_limit)
        self.assertEqual(quotas[quota_2.resource], quota_2.hard_limit)

    def test_destroy_quota(self):
        quota = utils.create_test_quota(context=self.ctx,
                                        project_id=self.project_id,
                                        resource=self.resource,
                                        limit=self.limit)
        dbapi.quota_destroy(self.ctx, quota.project_id, quota.resource)
        self.assertRaises(exception.ProjectQuotaNotFound, dbapi.quota_get,
                          self.ctx, quota.project_id, quota.resource)

    def test_update_quota(self):
        quota = utils.create_test_quota(context=self.ctx,
                                        project_id=self.project_id,
                                        resource=self.resource,
                                        limit=self.limit)
        dbapi.quota_update(self.ctx, quota.project_id,
                           quota.resource, 200)
        updated_quota = dbapi.quota_get(self.ctx, quota.project_id,
                                        quota.resource)
        self.assertEqual(updated_quota.hard_limit, 200)
