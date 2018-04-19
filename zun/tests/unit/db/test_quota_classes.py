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

from zun.common import consts
from zun.common import context
from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcdapi
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


class EtcdDbQuotaClassTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbQuotaClassTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_quota_class(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_quota_class(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_quota_class,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_get_quota_class(self, mock_db_inst,
                             mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota_class = utils.create_test_quota_class(context=self.context)
        mock_read.side_effect = lambda *args: utils.FakeEtcdResult(
            quota_class.as_dict())
        res = dbapi.quota_class_get(self.context, quota_class.class_name,
                                    quota_class.resource)
        self.assertEqual(quota_class.hard_limit, res.hard_limit)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_get_quota_class_by_default(self, mock_db_inst,
                                        mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota_class_1 = utils.create_test_quota_class(
            context=self.context, resource='fake_resource_1', hard_limit=10)
        quota_class_2 = utils.create_test_quota_class(
            context=self.context, resource='fake_resource_2', hard_limit=10)
        quota_classes = [quota_class_1, quota_class_2]
        mock_read.side_effect = lambda *args: utils.FakeEtcdMultipleResult(
            [quota_class_1.as_dict(), quota_class_2.as_dict()])
        res = dbapi.quota_class_get_default(self.context)
        self.assertEqual([qc.resource for qc in res],
                         [qc.resource for qc in quota_classes])
        self.assertEqual([q.hard_limit for q in res],
                         [q.hard_limit for q in quota_classes])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_get_quota_class_by_cls_name(self, mock_db_inst,
                                         mock_write, mock_read):
        cls_name = 'fake_class_name'
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota_class_1 = utils.create_test_quota_class(
            context=self.context, class_name=cls_name,
            resource='fake_resource_1', hard_limit=10)
        quota_class_2 = utils.create_test_quota_class(
            context=self.context, class_name=cls_name,
            resource='fake_resource_2', hard_limit=10)
        quota_classes = [quota_class_1, quota_class_2]
        mock_read.side_effect = lambda *args: utils.FakeEtcdMultipleResult(
            [quota_class_1.as_dict(), quota_class_2.as_dict()])
        res = dbapi.quota_class_get_all_by_name(self.context, cls_name)
        self.assertEqual([qc.resource for qc in res],
                         [qc.resource for qc in quota_classes])
        self.assertEqual([q.hard_limit for q in res],
                         [q.hard_limit for q in quota_classes])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, '_get_dbdriver_instance')
    def test_update_quota_class(self, mock_db_inst, mock_update,
                                mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        quota_class = utils.create_test_quota_class(context=self.context)
        new_hard_limit = 60
        mock_read.side_effect = lambda *args: utils.FakeEtcdResult(
            quota_class.as_dict())
        dbapi.quota_class_update(self.context, quota_class.class_name,
                                 quota_class.resource, new_hard_limit)
        self.assertEqual(new_hard_limit,
                         json.loads(mock_update.call_args_list[0][0][0].
                                    value.decode('utf-8'))['hard_limit'])
