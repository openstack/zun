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
from zun.db.etcd import api as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult

CONF = zun.conf.CONF


class DbVolumeMappingTestCase(base.DbTestCase):

    def setUp(self):
        super(DbVolumeMappingTestCase, self).setUp()

    def test_create_volume_mapping(self):
        utils.create_test_volume_mapping(context=self.context)

    def test_create_volume_mapping_already_exists(self):
        utils.create_test_volume_mapping(context=self.context,
                                         uuid='123')
        with self.assertRaisesRegex(exception.VolumeMappingAlreadyExists,
                                    'A volume mapping with UUID 123.*'):
            utils.create_test_volume_mapping(context=self.context,
                                             uuid='123')

    def test_get_volume_mapping_by_uuid(self):
        volume_mapping = utils.create_test_volume_mapping(context=self.context)
        res = dbapi.get_volume_mapping_by_uuid(self.context,
                                               volume_mapping.uuid)
        self.assertEqual(volume_mapping.id, res.id)
        self.assertEqual(volume_mapping.uuid, res.uuid)

    def test_get_volume_mapping_that_does_not_exist(self):
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.get_volume_mapping_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_volume_mappings(self):
        uuids = []
        for i in range(1, 6):
            volume_mapping = utils.create_test_volume_mapping(
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            uuids.append(six.text_type(volume_mapping['uuid']))
        res = dbapi.list_volume_mappings(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_volume_mappings_sorted(self):
        uuids = []
        for i in range(5):
            volume_mapping = utils.create_test_volume_mapping(
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            uuids.append(six.text_type(volume_mapping.uuid))
        res = dbapi.list_volume_mappings(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_volume_mappings,
                          self.context,
                          sort_key='foo')

    def test_list_volume_mappings_with_filters(self):
        volume_mapping1 = utils.create_test_volume_mapping(
            volume_provider='provider-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        volume_mapping2 = utils.create_test_volume_mapping(
            volume_provider='provider-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_volume_mappings(
            self.context, filters={'volume_provider': 'provider-one'})
        self.assertEqual([volume_mapping1.id], [r.id for r in res])

        res = dbapi.list_volume_mappings(
            self.context, filters={'volume_provider': 'provider-two'})
        self.assertEqual([volume_mapping2.id], [r.id for r in res])

        res = dbapi.list_volume_mappings(
            self.context, filters={'volume_provider': 'bad-provider'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_volume_mappings(
            self.context,
            filters={'volume_provider': volume_mapping1.volume_provider})
        self.assertEqual([volume_mapping1.id], [r.id for r in res])

    def test_destroy_volume_mapping(self):
        volume_mapping = utils.create_test_volume_mapping(context=self.context)
        dbapi.destroy_volume_mapping(self.context, volume_mapping.id)
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.get_volume_mapping_by_uuid,
                          self.context, volume_mapping.uuid)

    def test_destroy_volume_mapping_by_uuid(self):
        volume_mapping = utils.create_test_volume_mapping(context=self.context)
        dbapi.destroy_volume_mapping(self.context, volume_mapping.uuid)
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.get_volume_mapping_by_uuid,
                          self.context, volume_mapping.uuid)

    def test_destroy_volume_mapping_that_does_not_exist(self):
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.destroy_volume_mapping, self.context,
                          uuidutils.generate_uuid())

    def test_update_volume_mapping(self):
        volume_mapping = utils.create_test_volume_mapping(context=self.context)
        old_conn_info = volume_mapping.connection_info
        new_conn_info = 'new-conn-info'
        self.assertNotEqual(old_conn_info, new_conn_info)

        res = dbapi.update_volume_mapping(self.context, volume_mapping.id,
                                          {'connection_info': new_conn_info})
        self.assertEqual(new_conn_info, res.connection_info)

    def test_update_volume_mapping_not_found(self):
        volume_mapping_uuid = uuidutils.generate_uuid()
        new_conn_info = 'new-conn-info'
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.update_volume_mapping, self.context,
                          volume_mapping_uuid,
                          {'connection_info': new_conn_info})

    def test_update_volume_mapping_uuid(self):
        volume_mapping = utils.create_test_volume_mapping(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_volume_mapping, self.context,
                          volume_mapping.id, {'uuid': ''})


class EtcdDbVolumeMappingTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbVolumeMappingTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_volume_mapping(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_volume_mapping(context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_volume_mapping_already_exists(self, mock_write,
                                                  mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_volume_mapping(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_volume_mapping,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_volume_mapping_by_uuid(self, mock_ins, mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        volume_mapping = utils.create_test_volume_mapping(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            volume_mapping.as_dict())
        res = dbapi.get_volume_mapping_by_uuid(self.context,
                                               volume_mapping.uuid)
        self.assertEqual(volume_mapping.id, res.id)
        self.assertEqual(volume_mapping.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_get_volume_mapping_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.get_volume_mapping_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_volume_mappings(self, mock_ins, mock_write, mock_read):
        uuids = []
        volume_mappings = []
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(0, 6):
            volume_mapping = utils.create_test_volume_mapping(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='volume_mapping' + str(i))
            volume_mappings.append(volume_mapping.as_dict())
            uuids.append(six.text_type(volume_mapping['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            volume_mappings)
        res = dbapi.list_volume_mappings(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_volume_mappings_sorted(self, mock_ins,
                                         mock_write, mock_read):
        uuids = []
        volume_mappings = []
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(0, 6):
            volume_mapping = utils.create_test_volume_mapping(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='volume_mapping' + str(i))
            volume_mappings.append(volume_mapping.as_dict())
            uuids.append(six.text_type(volume_mapping['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            volume_mappings)
        res = dbapi.list_volume_mappings(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_volume_mappings,
                          self.context,
                          sort_key='wrong_key')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_volume_mappings_with_filters(self, mock_ins,
                                               mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound

        volume_mapping1 = utils.create_test_volume_mapping(
            name='volume_mapping1',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        volume_mapping2 = utils.create_test_volume_mapping(
            name='volume_mapping2',
            uuid=uuidutils.generate_uuid(),
            context=self.context,)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [volume_mapping1.as_dict(), volume_mapping2.as_dict()])

        res = dbapi.list_volume_mappings(
            self.context, filters={'uuid': volume_mapping1.uuid})
        self.assertEqual([volume_mapping1.id], [r.id for r in res])

        res = dbapi.list_volume_mappings(
            self.context, filters={'uuid': volume_mapping2.uuid})
        self.assertEqual([volume_mapping2.id], [r.id for r in res])

        res = dbapi.list_volume_mappings(
            self.context, filters={'uuid': 'unknow-uuid'})
        self.assertEqual([], [r.id for r in res])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_volume_mapping_by_uuid(self, mock_ins, mock_delete,
                                            mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        volume_mapping = utils.create_test_volume_mapping(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            volume_mapping.as_dict())
        dbapi.destroy_volume_mapping(self.context, volume_mapping.uuid)
        mock_delete.assert_called_once_with(
            '/volume_mappings/%s' % volume_mapping.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_volume_mapping_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.destroy_volume_mapping, self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_volume_mapping(self, mock_ins, mock_update,
                                   mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        volume_mapping = utils.create_test_volume_mapping(
            context=self.context)
        new_conn_info = 'new-conn-info'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            volume_mapping.as_dict())
        dbapi.update_volume_mapping(self.context, volume_mapping.uuid,
                                    {'container_info': new_conn_info})
        self.assertEqual(new_conn_info, json.loads(
            mock_update.call_args_list[0][0][0].value.decode('utf-8'))
            ['container_info'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_volume_mapping_not_found(self, mock_read):
        volume_mapping_uuid = uuidutils.generate_uuid()
        new_conn_info = 'new-conn-info'
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.VolumeMappingNotFound,
                          dbapi.update_volume_mapping, self.context,
                          volume_mapping_uuid,
                          {'container_info': new_conn_info})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_update_volume_mapping_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        volume_mapping = utils.create_test_volume_mapping(
            context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_volume_mapping, self.context,
                          volume_mapping.uuid, {'uuid': ''})
