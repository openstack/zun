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
import json

import etcd
from etcd import Client as etcd_client
import mock
from oslo_config import cfg

from zun.common import context
from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcdapi
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


class EtcdDbQuotaTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbQuotaTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_quota(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_quota(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_quota,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_get_quota(self, mock_db_inst,
                       mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota = utils.create_test_quota(context=self.context)
        mock_read.side_effect = lambda *args: utils.FakeEtcdResult(
            quota.as_dict())
        res = dbapi.quota_get(self.context, quota.project_id,
                              quota.resource)
        self.assertEqual(quota.hard_limit, res.hard_limit)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_get_all_project_quota(self, mock_db_inst,
                                   mock_write, mock_read):
        prj_id = 'fake_project_id'
        resources = ['fake_resource_1', 'fake_resource_2']
        hard_limits = [10, 20]
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota_1 = utils.create_test_quota(
            context=self.context, project_id=prj_id,
            resource=resources[0], hard_limit=hard_limits[0])
        quota_2 = utils.create_test_quota(
            context=self.context, project_id=prj_id,
            resource=resources[1], hard_limit=hard_limits[1])
        quotas = [quota_1, quota_2]
        mock_read.side_effect = lambda *args: utils.FakeEtcdMultipleResult(
            [quota_1.as_dict(), quota_2.as_dict()])
        res = dbapi.quota_get_all_by_project(self.context, prj_id)
        self.assertEqual([q.resource for q in res],
                         [q.resource for q in quotas])
        self.assertEqual([q.hard_limit for q in res],
                         [q.hard_limit for q in quotas])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_destroy_quota(self, mock_db_inst, mock_delete,
                           mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota = utils.create_test_quota(context=self.context)
        mock_read.side_effect = lambda *args: utils.FakeEtcdResult(
            quota.as_dict())
        dbapi.quota_destroy(
            self.context, quota.project_id, quota.resource)
        mock_delete.assert_called_once_with(
            '/quotas/{}/{}' . format(quota.project_id, quota.resource))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_update_quota(self, mock_db_inst, mock_update,
                          mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota = utils.create_test_quota(context=self.context)
        new_hard_limit = 60
        mock_read.side_effect = lambda *args: utils.FakeEtcdResult(
            quota.as_dict())
        dbapi.quota_update(self.context, quota.project_id, quota.resource,
                           new_hard_limit)
        self.assertEqual(new_hard_limit,
                         json.loads(mock_update.call_args_list[0][0][0].
                                    value.decode('utf-8'))['hard_limit'])
