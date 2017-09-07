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

import mock

from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestComputeNodeObject(base.DbTestCase):

    def setUp(self):
        super(TestComputeNodeObject, self).setUp()
        self.fake_numa_topology = utils.get_test_numa_topology()
        self.fake_compute_node = utils.get_test_compute_node(
            numa_topology=self.fake_numa_topology)

    def test_get_by_uuid(self):
        uuid = self.fake_compute_node['uuid']
        with mock.patch.object(self.dbapi, 'get_compute_node',
                               autospec=True) as mock_get_compute_node:
            mock_get_compute_node.return_value = self.fake_compute_node
            compute_node = objects.ComputeNode.get_by_uuid(self.context, uuid)
            mock_get_compute_node.assert_called_once_with(
                self.context, uuid)
            self.assertEqual(self.context, compute_node._context)

    def test_get_by_name(self):
        hostname = self.fake_compute_node['hostname']
        with mock.patch.object(self.dbapi, 'get_compute_node_by_hostname',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_compute_node
            compute_node = objects.ComputeNode.get_by_name(
                self.context, hostname)
            mock_get.assert_called_once_with(self.context, hostname)
            self.assertEqual(self.context, compute_node._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_compute_nodes',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_compute_node]
            compute_nodes = objects.ComputeNode.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(compute_nodes, HasLength(1))
            self.assertIsInstance(compute_nodes[0], objects.ComputeNode)
            self.assertEqual(self.context, compute_nodes[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_compute_nodes',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_compute_node]
            filt = {'hostname': 'test'}
            compute_nodes = objects.ComputeNode.list(
                self.context, filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(compute_nodes, HasLength(1))
            self.assertIsInstance(compute_nodes[0], objects.ComputeNode)
            self.assertEqual(self.context, compute_nodes[0]._context)
            mock_get_list.assert_called_once_with(
                self.context, filters=filt, limit=None, marker=None,
                sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_compute_node',
                               autospec=True) as mock_create:
            mock_create.return_value = self.fake_compute_node
            compute_node_dict = dict(self.fake_compute_node)
            compute_node_dict['numa_topology'] = objects.NUMATopology\
                ._from_dict(compute_node_dict['numa_topology'])
            compute_node = objects.ComputeNode(
                self.context, **compute_node_dict)
            compute_node.create(self.context)
            mock_create.assert_called_once_with(
                self.context, self.fake_compute_node)
            self.assertEqual(self.context, compute_node._context)

    def test_destroy(self):
        uuid = self.fake_compute_node['uuid']
        with mock.patch.object(self.dbapi, 'get_compute_node',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_compute_node
            with mock.patch.object(self.dbapi, 'destroy_compute_node',
                                   autospec=True) as mock_destroy:
                compute_node = objects.ComputeNode.get_by_uuid(
                    self.context, uuid)
                compute_node.destroy()
                mock_get.assert_called_once_with(self.context, uuid)
                mock_destroy.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, compute_node._context)

    def test_save(self):
        uuid = self.fake_compute_node['uuid']
        with mock.patch.object(self.dbapi, 'get_compute_node',
                               autospec=True) as mock_get:
            mock_get.return_value = self.fake_compute_node
            with mock.patch.object(self.dbapi, 'update_compute_node',
                                   autospec=True) as mock_update:
                compute_node = objects.ComputeNode.get_by_uuid(
                    self.context, uuid)
                compute_node.hostname = 'myhostname'
                compute_node.save()

                mock_get.assert_called_once_with(self.context, uuid)
                mock_update.assert_called_once_with(
                    None, uuid,
                    {'hostname': 'myhostname'})
                self.assertEqual(self.context, compute_node._context)

    def test_refresh(self):
        uuid = self.fake_compute_node['uuid']
        hostname = self.fake_compute_node['hostname']
        new_hostname = 'myhostname'
        returns = [dict(self.fake_compute_node, hostname=hostname),
                   dict(self.fake_compute_node, hostname=new_hostname)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_compute_node',
                               side_effect=returns,
                               autospec=True) as mock_get:
            compute_node = objects.ComputeNode.get_by_uuid(self.context, uuid)
            self.assertEqual(hostname, compute_node.hostname)
            compute_node.refresh()
            self.assertEqual(new_hostname, compute_node.hostname)
            self.assertEqual(expected, mock_get.call_args_list)
            self.assertEqual(self.context, compute_node._context)
