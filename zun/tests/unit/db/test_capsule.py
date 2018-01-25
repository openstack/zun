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

"""Tests for manipulating Capsule via the DB API"""
import json

import etcd
from etcd import Client as etcd_client
import mock
from oslo_config import cfg
from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcdapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult


CONF = zun.conf.CONF


class SqlDbCapsuleTestCase(base.DbTestCase):

    def setUp(self):
        super(SqlDbCapsuleTestCase, self).setUp()

    def test_create_capsule(self):
        utils.create_test_capsule(context=self.context)

    def test_create_capsule_already_exists(self):
        utils.create_test_capsule(context=self.context)
        self.assertRaises(exception.CapsuleAlreadyExists,
                          utils.create_test_capsule,
                          context=self.context)

    def test_get_capsule_by_uuid(self):
        capsule = utils.create_test_capsule(context=self.context)
        res = dbapi.get_capsule_by_uuid(self.context,
                                        capsule.uuid)
        self.assertEqual(capsule.id, res.id)
        self.assertEqual(capsule.uuid, res.uuid)

    def test_get_capsule_by_meta_name(self):
        capsule = utils.create_test_capsule(context=self.context)
        res = dbapi.get_capsule_by_meta_name(self.context,
                                             capsule.meta_name)
        self.assertEqual(capsule.id, res.id)
        self.assertEqual(capsule.meta_name, res.meta_name)

    def test_get_non_exists_capsule(self):
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.get_capsule_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_capsules(self):
        uuids = []
        for i in range(1, 6):
            capsule = utils.create_test_capsule(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='capsule' + str(i)
            )
            uuids.append(six.text_type(capsule['uuid']))
        res = dbapi.list_capsules(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_capsules_sorted_with_valid_sort_key(self):
        uuids = []
        for i in range(1, 6):
            capsule = utils.create_test_capsule(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='capsule' + str(i)
            )
            uuids.append(six.text_type(capsule['uuid']))
        res = dbapi.list_capsules(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

    def test_list_capsules_sorted_with_invalid_sort_key(self):
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_capsules,
                          self.context,
                          sort_key='foo')

    def test_list_capsules_with_filters(self):
        capsule1 = utils.create_test_capsule(
            name='capsule1',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        capsule2 = utils.create_test_capsule(
            name='capsule2',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_capsules(
            self.context, filters={'uuid': capsule1.uuid})
        self.assertEqual([capsule1.id], [r.id for r in res])

        res = dbapi.list_capsules(
            self.context, filters={'uuid': capsule2.uuid})
        self.assertEqual([capsule2.id], [r.id for r in res])

        res = dbapi.list_capsules(
            self.context, filters={'uuid': 'unknow-uuid'})
        self.assertEqual([], [r.id for r in res])

    def test_destroy_capsule(self):
        capsule = utils.create_test_capsule(context=self.context)
        dbapi.destroy_capsule(self.context, capsule.id)
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.get_capsule_by_uuid,
                          self.context,
                          capsule.uuid)

    def test_destroy_capsule_by_uuid(self):
        capsule = utils.create_test_capsule(context=self.context)
        dbapi.destroy_capsule(self.context, capsule.uuid)
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.get_capsule_by_uuid,
                          self.context,
                          capsule.uuid)

    def test_destroy_non_exists_capsule(self):
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.destroy_capsule,
                          self.context,
                          uuidutils.generate_uuid())

    def test_update_capsule(self):
        capsule = utils.create_test_capsule(context=self.context)
        current_meta_name = capsule.meta_name
        new_meta_name = 'new-meta-name'
        self.assertNotEqual(current_meta_name, new_meta_name)

        res = dbapi.update_capsule(self.context, capsule.id,
                                   {'meta_name': new_meta_name})
        self.assertEqual(new_meta_name, res.meta_name)

    def test_update_capsule_not_found(self):
        capsule_uuid = uuidutils.generate_uuid()
        new_meta_name = 'new-meta-name'
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.update_capsule,
                          self.context, capsule_uuid,
                          {'meta_name': new_meta_name})

    def test_update_capsule_uuid(self):
        capsule = utils.create_test_capsule(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_capsule, self.context,
                          capsule.id, {'uuid': ''})


class EtcdDbCapsuleTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbCapsuleTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_capsule(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_capsule(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_capsule,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_capsule_by_uuid(self, mock_db_inst,
                                 mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        capsule = utils.create_test_capsule(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            capsule.as_dict())
        res = dbapi.get_capsule_by_uuid(self.context,
                                        capsule.uuid)
        self.assertEqual(capsule.id, res.id)
        self.assertEqual(capsule.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_capsule_by_meta_name(self, mock_db_inst,
                                      mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        capsule = utils.create_test_capsule(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [capsule.as_dict()])
        res = dbapi.get_capsule_by_meta_name(
            self.context, capsule.meta_name)
        self.assertEqual(capsule.id, res.id)
        self.assertEqual(capsule.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_get_nonexists_capsule(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.get_capsule_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_capsules(self, mock_db_inst, mock_write, mock_read):
        uuids = []
        capsules = []
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            capsule = utils.create_test_capsule(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='capsule' + str(i))
            capsules.append(capsule.as_dict())
            uuids.append(six.text_type(capsule['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            capsules)
        res = dbapi.list_capsules(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_capsules_sorted(self, mock_db_inst,
                                  mock_write, mock_read):
        uuids = []
        capsules = []
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            capsule = utils.create_test_capsule(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='capsule' + str(i))
            capsules.append(capsule.as_dict())
            uuids.append(six.text_type(capsule['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            capsules)
        res = dbapi.list_capsules(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_capsules,
                          self.context,
                          sort_key='foo')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_capsules_with_filters(self, mock_db_inst,
                                        mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound

        capsule1 = utils.create_test_capsule(
            name='capsule1',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        capsule2 = utils.create_test_capsule(
            name='capsule2',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [capsule1.as_dict(), capsule2.as_dict()])

        res = dbapi.list_capsules(
            self.context, filters={'uuid': capsule1.uuid})
        self.assertEqual([capsule1.id], [r.id for r in res])

        res = dbapi.list_capsules(
            self.context, filters={'uuid': capsule2.uuid})
        self.assertEqual([capsule2.id], [r.id for r in res])

        res = dbapi.list_capsules(
            self.context, filters={'uuid': 'unknow-uuid'})
        self.assertEqual([], [r.id for r in res])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_capsule_by_uuid(self, mock_db_inst, mock_delete,
                                     mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        capsule = utils.create_test_capsule(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            capsule.as_dict())
        dbapi.destroy_capsule(self.context, capsule.uuid)
        mock_delete.assert_called_once_with('/capsules/%s' % capsule.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_non_exists_capsule(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.destroy_capsule, self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_capsule(self, mock_db_inst,
                            mock_update, mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        capsule = utils.create_test_capsule(context=self.context)
        new_meta_name = 'new_meta_name'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            capsule.as_dict())
        dbapi.update_capsule(self.context, capsule.uuid,
                             {'meta_name': new_meta_name})
        self.assertEqual(new_meta_name, json.loads(
            mock_update.call_args_list[0][0][0].value.decode('utf-8'))
            ['meta_name'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_capsule_not_found(self, mock_read):
        capsule_uuid = uuidutils.generate_uuid()
        new_meta_name = 'new-meta-name'
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.CapsuleNotFound,
                          dbapi.update_capsule, self.context,
                          capsule_uuid, {'meta_name': new_meta_name})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_update_capsule_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        capsule = utils.create_test_capsule(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_capsule, self.context,
                          capsule.uuid, {'uuid': ''})
