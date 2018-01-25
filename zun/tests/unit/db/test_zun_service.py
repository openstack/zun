# Copyright 2016 IBM, Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

import etcd
from etcd import Client as etcd_client
from oslo_config import cfg
from oslo_serialization import jsonutils as json

from zun.common import exception
from zun.db import api as dbapi
from zun.db.etcd import api as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult


class DbZunServiceTestCase(base.DbTestCase):

    def setUp(self):
        super(DbZunServiceTestCase, self).setUp()

    def test_create_zun_service(self):
        utils.create_test_zun_service()

    def test_create_zun_service_failure_for_dup(self):
        utils.create_test_zun_service()
        self.assertRaises(exception.ZunServiceAlreadyExists,
                          utils.create_test_zun_service)

    def test_get_zun_service(self):
        ms = utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            ms['host'], ms['binary'])
        self.assertEqual(ms.id, res.id)

    def test_get_zun_service_failure(self):
        utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            'fakehost1', 'fake-bin1')
        self.assertIsNone(res)

    def test_update_zun_service(self):
        ms = utils.create_test_zun_service()
        d2 = True
        update = {'disabled': d2}
        ms1 = self.dbapi.update_zun_service(ms['host'], ms['binary'], update)
        self.assertEqual(ms['id'], ms1['id'])
        self.assertEqual(d2, ms1['disabled'])
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertEqual(ms1['id'], res['id'])
        self.assertEqual(d2, res['disabled'])

    def test_update_zun_service_failure(self):
        fake_update = {'fake_field': 'fake_value'}
        self.assertRaises(exception.ZunServiceNotFound,
                          self.dbapi.update_zun_service,
                          'fakehost1', 'fake-bin1', fake_update)

    def test_destroy_zun_service(self):
        ms = utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertEqual(res['id'], ms['id'])
        self.dbapi.destroy_zun_service(ms['host'], ms['binary'])
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertIsNone(res)

    def test_destroy_zun_service_failure(self):
        self.assertRaises(exception.ZunServiceNotFound,
                          self.dbapi.destroy_zun_service,
                          'fakehostsssss', 'fakessss-bin1')

    def test_list_zun_services(self):
        fake_ms_params = {
            'report_count': 1010,
            'host': 'FakeHost',
            'binary': 'FakeBin',
            'disabled': False,
            'disabled_reason': 'FakeReason'
        }
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services()
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

        fake_ms_params['binary'] = 'FakeBin1'
        fake_ms_params['disabled'] = True
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services(filters={'disabled': True})
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

    def test_list_zun_services_by_binary(self):
        fake_ms_params = {
            'report_count': 1010,
            'host': 'FakeHost',
            'binary': 'FakeBin',
            'disabled': False,
            'disabled_reason': 'FakeReason'
        }
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services_by_binary(
            binary=fake_ms_params['binary'])
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

        res = self.dbapi.list_zun_services_by_binary(binary='none')
        self.assertEqual(0, len(res))


class EtcdDbZunServiceTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbZunServiceTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_zun_service(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_zun_service()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_zun_service_already_exists(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_zun_service()
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_zun_service)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_zun_service(self, mock_ins, mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            zun_service.as_dict())
        res = dbapi.get_zun_service(
            self.context, zun_service.host, zun_service.binary)
        self.assertEqual(zun_service.host, res.host)
        self.assertEqual(zun_service.binary, res.binary)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_zun_service_not_found(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        res = dbapi.get_zun_service(
            self.context, 'wrong_host_name', zun_service.binary)
        self.assertIsNone(res)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_zun_services(self, mock_ins, mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        service_1 = utils.create_test_zun_service(host='host_1')
        service_2 = utils.create_test_zun_service(host='host_2')
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [service_1.as_dict(), service_2.as_dict()])
        res = dbapi.list_zun_services(self.context)
        self.assertEqual(2, len(res))
        self.assertEqual('host_1', res[0].host)
        self.assertEqual('host_2', res[1].host)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_zun_services_by_binary(self, mock_ins,
                                         mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        service_1 = utils.create_test_zun_service(
            host='host_1', binary='binary_1')
        service_2 = utils.create_test_zun_service(
            host='host_2', binary='binary_2')
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [service_1.as_dict(), service_2.as_dict()])
        res = dbapi.list_zun_services_by_binary(
            self.context, 'binary_1')
        self.assertEqual(1, len(res))
        self.assertEqual('host_1', res[0].host)
        self.assertEqual('binary_1', res[0].binary)

        res = dbapi.list_zun_services_by_binary(
            self.context, 'fake-binary')
        self.assertEqual(0, len(res))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_zun_service(self, mock_ins, mock_delete,
                                 mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            zun_service.as_dict())
        dbapi.destroy_zun_service(zun_service.host,
                                  zun_service.binary)
        mock_delete.assert_called_once_with(
            '/zun_services/%s' % zun_service.host + '_' + zun_service.binary)

    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_zun_service_not_exist(self, mock_ins, mock_delete):
        mock_ins.return_value = etcd_api.get_backend()
        mock_delete.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ZunServiceNotFound,
                          dbapi.destroy_zun_service,
                          'host_1', 'binary_1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_zun_service(self, mock_ins, mock_update,
                                mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        service = utils.create_test_zun_service()
        new_host = 'new-host'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            service.as_dict())
        dbapi.update_zun_service(service.host, service.binary,
                                 {'host': new_host})
        self.assertEqual(new_host, json.loads(
            mock_update.call_args_list[0][0][0].value)['host'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_zun_service_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ZunServiceNotFound,
                          dbapi.update_zun_service,
                          'host_1', 'binary_1', {'host': 'new-host'})
