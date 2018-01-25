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

"""Tests for manipulating compute nodes via the DB API"""
import json
import mock
from oslo_config import cfg
from oslo_utils import uuidutils
import six

import etcd
from etcd import Client as etcd_client
from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcdapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult

CONF = zun.conf.CONF


class DbComputeNodeTestCase(base.DbTestCase):

    def setUp(self):
        super(DbComputeNodeTestCase, self).setUp()

    def test_create_compute_node(self):
        utils.create_test_compute_node(context=self.context)

    def test_create_compute_node_already_exists(self):
        utils.create_test_compute_node(
            context=self.context, uuid='123')
        with self.assertRaisesRegex(exception.ComputeNodeAlreadyExists,
                                    'A compute node with UUID 123.*'):
            utils.create_test_compute_node(
                context=self.context, uuid='123')

    def test_get_compute_node_by_uuid(self):
        node = utils.create_test_compute_node(context=self.context)
        res = dbapi.get_compute_node(
            self.context, node.uuid)
        self.assertEqual(node.uuid, res.uuid)
        self.assertEqual(node.hostname, res.hostname)

    def test_get_compute_node_by_hostname(self):
        node = utils.create_test_compute_node(context=self.context)
        res = dbapi.get_compute_node_by_hostname(
            self.context, node.hostname)
        self.assertEqual(node.uuid, res.uuid)
        self.assertEqual(node.hostname, res.hostname)

    def test_get_compute_node_that_does_not_exist(self):
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.get_compute_node,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_compute_nodes(self):
        uuids = []
        for i in range(1, 6):
            node = utils.create_test_compute_node(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                hostname='node' + str(i))
            uuids.append(six.text_type(node['uuid']))
        res = dbapi.list_compute_nodes(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_compute_nodes_sorted(self):
        uuids = []
        for i in range(5):
            node = utils.create_test_compute_node(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                hostname='node' + str(i))
            uuids.append(six.text_type(node.uuid))
        res = dbapi.list_compute_nodes(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_compute_nodes,
                          self.context,
                          sort_key='foo')

    def test_list_compute_nodes_with_filters(self):
        node1 = utils.create_test_compute_node(
            hostname='node-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        node2 = utils.create_test_compute_node(
            hostname='node-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_compute_nodes(
            self.context, filters={'hostname': 'node-one'})
        self.assertEqual([node1.uuid], [r.uuid for r in res])

        res = dbapi.list_compute_nodes(
            self.context, filters={'hostname': 'node-two'})
        self.assertEqual([node2.uuid], [r.uuid for r in res])

        res = dbapi.list_compute_nodes(
            self.context, filters={'hostname': 'bad-node'})
        self.assertEqual([], [r.uuid for r in res])

        res = dbapi.list_compute_nodes(
            self.context,
            filters={'hostname': node1.hostname})
        self.assertEqual([node1.uuid], [r.uuid for r in res])

    def test_destroy_compute_node(self):
        node = utils.create_test_compute_node(context=self.context)
        dbapi.destroy_compute_node(self.context, node.uuid)
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.get_compute_node,
                          self.context, node.uuid)

    def test_destroy_compute_node_by_uuid(self):
        node = utils.create_test_compute_node(context=self.context)
        dbapi.destroy_compute_node(self.context, node.uuid)
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.get_compute_node,
                          self.context, node.uuid)

    def test_destroy_compute_node_that_does_not_exist(self):
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.destroy_compute_node, self.context,
                          uuidutils.generate_uuid())

    def test_update_compute_node(self):
        node = utils.create_test_compute_node(context=self.context)
        old_hostname = node.hostname
        new_hostname = 'new-hostname'
        self.assertNotEqual(old_hostname, new_hostname)

        res = dbapi.update_compute_node(
            self.context, node.uuid, {'hostname': new_hostname})
        self.assertEqual(new_hostname, res.hostname)

    def test_update_compute_node_not_found(self):
        node_uuid = uuidutils.generate_uuid()
        new_hostname = 'new-hostname'
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.update_compute_node, self.context,
                          node_uuid, {'hostname': new_hostname})

    def test_update_compute_node_uuid(self):
        node = utils.create_test_compute_node(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_compute_node, self.context,
                          node.uuid, {'uuid': ''})


class EtcdDbComputeNodeTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbComputeNodeTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_compute_node(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_compute_node(context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_compute_node_already_exists(self, mock_write,
                                                mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_compute_node(context=self.context, hostname='123')
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_compute_node,
                          context=self.context, hostname='123')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_compute_node_by_uuid(self, mock_db_inst,
                                      mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        compute_node = utils.create_test_compute_node(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            compute_node.as_dict())
        res = dbapi.get_compute_node(self.context, compute_node.uuid)
        self.assertEqual(compute_node.uuid, res.uuid)
        self.assertEqual(compute_node.hostname, res.hostname)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_compute_node_by_name(self, mock_db_inst,
                                      mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        node = utils.create_test_compute_node(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            node.as_dict())
        res = dbapi.get_compute_node(self.context, node.hostname)
        self.assertEqual(node.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_get_compute_node_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.get_compute_node,
                          self.context, 'fake-ident')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_compute_nodes(self, mock_db_inst, mock_write, mock_read):
        hostnames = []
        compute_nodes = []
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            res_class = utils.create_test_compute_node(
                context=self.context, hostname='class' + str(i))
            compute_nodes.append(res_class.as_dict())
            hostnames.append(six.text_type(res_class['hostname']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            compute_nodes)
        res = dbapi.list_compute_nodes(self.context)
        res_names = [r.hostname for r in res]
        self.assertEqual(sorted(hostnames), sorted(res_names))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_compute_nodes_sorted(self, mock_db_inst,
                                       mock_write, mock_read):
        hostnames = []
        compute_nodes = []
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            res_class = utils.create_test_compute_node(
                context=self.context, hostname='class' + str(i))
            compute_nodes.append(res_class.as_dict())
            hostnames.append(six.text_type(res_class['hostname']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            compute_nodes)
        res = dbapi.list_compute_nodes(self.context, sort_key='hostname')
        res_names = [r.hostname for r in res]
        self.assertEqual(sorted(hostnames), res_names)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_compute_node(self, mock_db_inst, mock_delete,
                                  mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        compute_node = utils.create_test_compute_node(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            compute_node.as_dict())
        dbapi.destroy_compute_node(self.context, compute_node.uuid)
        mock_delete.assert_called_once_with(
            '/compute_nodes/%s' % compute_node.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_compute_node_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.destroy_compute_node,
                          self.context,
                          'ca3e2a25-2901-438d-8157-de7ffd68d535')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_compute_node(self, mock_db_inst, mock_update,
                                 mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        compute_node = utils.create_test_compute_node(
            context=self.context)
        old_name = compute_node.hostname
        new_name = 'new-name'
        self.assertNotEqual(old_name, new_name)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            compute_node.as_dict())
        dbapi.update_compute_node(
            self.context, compute_node.uuid, {'hostname': new_name})
        self.assertEqual(new_name, json.loads(
            mock_update.call_args_list[0][0][0].value)['hostname'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_compute_node_not_found(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        new_name = 'new-name'
        self.assertRaises(exception.ComputeNodeNotFound,
                          dbapi.update_compute_node,
                          self.context,
                          'ca3e2a25-2901-438d-8157-de7ffd68d535',
                          {'hostname': new_name})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_update_compute_node_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        compute_node = utils.create_test_compute_node(
            context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_compute_node,
                          self.context, compute_node.uuid,
                          {'uuid': ''})
