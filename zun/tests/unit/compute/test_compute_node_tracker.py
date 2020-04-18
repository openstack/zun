#    Copyright 2016 IBM Corp.
#
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

from unittest import mock

from zun.compute import claims
from zun.compute import compute_node_tracker
from zun import objects
from zun.tests import base
from zun.tests.unit.container import fake_driver
from zun.tests.unit.objects import utils as obj_utils


class TestNodeStracker(base.TestCase):

    def setUp(self):
        super(TestNodeStracker, self).setUp()
        self.container_driver = fake_driver.FakeDriver()
        self.capsule_driver = fake_driver.FakeDriver()
        self.report_client_mock = mock.MagicMock()
        self._resource_tracker = compute_node_tracker.ComputeNodeTracker(
            'testhost', self.container_driver, self.capsule_driver,
            self.report_client_mock)

    @mock.patch.object(compute_node_tracker.ComputeNodeTracker, '_update')
    @mock.patch.object(compute_node_tracker.ComputeNodeTracker,
                       '_update_usage_from_container_update')
    @mock.patch.object(claims, 'UpdateClaim')
    def test_container_update_same_resource(self, mock_claim,
                                            mock_container_update,
                                            mock_update):
        container1 = obj_utils.get_test_container(
            self.context, cpu=1, memory=1024)
        container2 = obj_utils.get_test_container(
            self.context, cpu=1, memory=1024)

        self._resource_tracker.container_update_claim(
            self.context, container1, container2)
        self.assertFalse(mock_claim.called)
        self.assertFalse(mock_container_update.called)
        self.assertFalse(mock_update.called)

    @mock.patch.object(
        compute_node_tracker.ComputeNodeTracker, '_get_compute_node')
    @mock.patch.object(compute_node_tracker.ComputeNodeTracker, '_update')
    @mock.patch.object(compute_node_tracker.ComputeNodeTracker,
                       '_update_usage_from_container_update')
    @mock.patch.object(claims, 'UpdateClaim')
    def test_container_update(self, mock_claim, mock_container_update,
                              mock_update, mock_get_node):
        container1 = obj_utils.get_test_container(
            self.context, cpu=1, memory=1024)
        container2 = obj_utils.get_test_container(
            self.context, cpu2=2, memory=2048)
        node = objects.ComputeNode(self.context)
        node.cpu = 10
        node.memory = 3072
        mock_get_node.return_value = node

        self._resource_tracker.container_update_claim(
            self.context, container1, container2)
        self.assertTrue(mock_claim.called)
        self.assertTrue(mock_container_update.called)
        self.assertTrue(mock_update.called)
