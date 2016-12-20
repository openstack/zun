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

import json
import mock

import etcd
from etcd import Client as etcd_client
from oslo_config import cfg

from zun.common import exception
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult


class EtcdDbZunServiceTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('db_type', 'etcd')
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
    def test_get_zun_service(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            zun_service.as_dict())
        res = dbapi.Connection.get_zun_service(
            self.context, zun_service.host, zun_service.binary)
        self.assertEqual(zun_service.host, res.host)
        self.assertEqual(zun_service.binary, res.binary)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_zun_service_not_found(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        res = dbapi.Connection.get_zun_service(
            self.context, 'wrong_host_name', zun_service.binary)
        self.assertIsNone(res)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_zun_service_list(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        service_1 = utils.create_test_zun_service(host='host_1')
        service_2 = utils.create_test_zun_service(host='host_2')
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [service_1.as_dict(), service_2.as_dict()])
        res = dbapi.Connection.get_zun_service_list(self.context)
        self.assertEqual(2, len(res))
        self.assertEqual('host_1', res[0].host)
        self.assertEqual('host_2', res[1].host)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    def test_destroy_zun_service(self, mock_delete, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        zun_service = utils.create_test_zun_service()
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            zun_service.as_dict())
        dbapi.Connection.destroy_zun_service(zun_service.host,
                                             zun_service.binary)
        mock_delete.assert_called_once_with(
            '/zun_services/%s' % zun_service.host+'_'+zun_service.binary)

    @mock.patch.object(etcd_client, 'delete')
    def test_destroy_zun_service_not_exist(self, mock_delete):
        mock_delete.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ZunServiceNotFound,
                          dbapi.Connection.destroy_zun_service,
                          'host_1', 'binary_1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    def test_update_zun_service(self, mock_update, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        service = utils.create_test_zun_service()
        new_host = 'new-host'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            service.as_dict())
        dbapi.Connection.update_zun_service(service.host, service.binary,
                                            {'host': new_host})
        self.assertEqual(new_host, json.loads(
            mock_update.call_args_list[0][0][0].value)['host'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_zun_service_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ZunServiceNotFound,
                          dbapi.Connection.update_zun_service,
                          'host_1', 'binary_1', {'host': 'new-host'})
