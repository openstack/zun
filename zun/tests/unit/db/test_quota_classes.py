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

from zun.common import consts
from zun.common import context
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DBQuotaClassesTestCase(base.DbTestCase):

    def setUp(self):
        super(DBQuotaClassesTestCase, self).setUp()
        self.ctx = context.get_admin_context()
        self.class_name = 'default'
        self.resource = 'containers'
        self.limit = 100

    def test_create_quota_class(self):
        quota_class = utils.create_test_quota_class(context=self.ctx,
                                                    class_name=self.class_name,
                                                    resource=self.resource,
                                                    limit=self.limit)
        self.assertEqual(quota_class.class_name, self.class_name)
        self.assertEqual(quota_class.resource, self.resource)
        self.assertEqual(quota_class.hard_limit, self.limit)

    def test_get_quota_class(self):
        quota_class = utils.create_test_quota_class(context=self.ctx,
                                                    class_name=self.class_name,
                                                    resource=self.resource,
                                                    limit=self.limit)
        res = dbapi.quota_class_get(context=self.ctx,
                                    class_name=quota_class.class_name,
                                    resource=quota_class.resource)
        self.assertEqual(quota_class.class_name, res.class_name)
        self.assertEqual(quota_class.resource, res.resource)
        self.assertEqual(quota_class.hard_limit, res.hard_limit)

    def test_get_default_quota_class(self):
        default_quota_class_resource_1 = utils.create_test_quota_class(
            context=self.ctx,
            class_name=consts.DEFAULT_QUOTA_CLASS_NAME,
            resource='resource_1',
            limit=10)

        default_quota_class_resource_2 = utils.create_test_quota_class(
            context=self.ctx,
            class_name=consts.DEFAULT_QUOTA_CLASS_NAME,
            resource='resource_2',
            limit=20)

        res = dbapi.quota_class_get_default(self.ctx)
        self.assertEqual(res['class_name'],
                         consts.DEFAULT_QUOTA_CLASS_NAME)
        self.assertEqual(res[default_quota_class_resource_1.resource],
                         default_quota_class_resource_1.hard_limit)
        self.assertEqual(res[default_quota_class_resource_2.resource],
                         default_quota_class_resource_2.hard_limit)

    def test_get_all_by_name_quota_class(self):
        quota_class_resource_1 = utils.create_test_quota_class(
            context=self.ctx,
            class_name='class_1',
            resource='resource_1',
            limit=10)

        quota_class_resource_2 = utils.create_test_quota_class(
            context=self.ctx,
            class_name='class_1',
            resource='resource_2',
            limit=20)

        res = dbapi.quota_class_get_all_by_name(self.ctx, 'class_1')
        self.assertEqual(res['class_name'],
                         'class_1')
        self.assertEqual(res[quota_class_resource_1.resource],
                         quota_class_resource_1.hard_limit)
        self.assertEqual(res[quota_class_resource_2.resource],
                         quota_class_resource_2.hard_limit)

    def test_update_quota_class(self):
        quota_class = utils.create_test_quota_class(context=self.ctx,
                                                    class_name=self.class_name,
                                                    resource=self.resource,
                                                    limit=self.limit)
        dbapi.quota_class_update(
            self.ctx, quota_class.class_name,
            quota_class.resource, 200)
        updated_quota_class = dbapi.quota_class_get(
            self.ctx, quota_class.class_name,
            quota_class.resource)
        self.assertEqual(updated_quota_class.hard_limit, 200)
