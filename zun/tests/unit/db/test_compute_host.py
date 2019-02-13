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

from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

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
