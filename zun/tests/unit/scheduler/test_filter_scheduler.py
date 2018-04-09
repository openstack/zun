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

from zun.api import servicegroup
from zun.common import context
from zun.common import exception
from zun import objects
from zun.scheduler import filter_scheduler
from zun.tests import base
from zun.tests.unit.db import utils
from zun.tests.unit.scheduler.fakes import FakeService


class FilterSchedulerTestCase(base.TestCase):
    """Test case for Filter Scheduler."""

    driver_cls = filter_scheduler.FilterScheduler

    def setUp(self):
        super(FilterSchedulerTestCase, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')
        self.driver = self.driver_cls()

    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    @mock.patch.object(objects.ComputeNode, 'list')
    @mock.patch.object(objects.ZunService, 'list_by_binary')
    @mock.patch('random.choice')
    def test_select_destinations(self, mock_random_choice,
                                 mock_list_by_binary, mock_compute_list,
                                 mock_service_is_up):
        all_services = [FakeService('service1', 'host1'),
                        FakeService('service2', 'host2'),
                        FakeService('service3', 'host3'),
                        FakeService('service4', 'host4')]

        def _return_services(*args, **kwargs):
            return all_services

        self.driver.servicegroup_api.service_is_up = mock.Mock(
            return_value=True)
        mock_list_by_binary.side_effect = _return_services
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        node1 = objects.ComputeNode(self.context)
        node1.cpus = 48
        node1.cpu_used = 0.0
        node1.mem_total = 1024 * 128
        node1.mem_used = 1024 * 4
        node1.mem_free = 1024 * 124
        node1.disk_total = 80
        node1.disk_used = 20
        node1.hostname = 'host1'
        node1.numa_topology = None
        node1.labels = {}
        node1.pci_device_pools = None
        node1.disk_quota_supported = True
        node2 = objects.ComputeNode(self.context)
        node2.cpus = 48
        node2.cpu_used = 0.0
        node2.mem_total = 1024 * 128
        node2.mem_used = 1024 * 4
        node2.mem_free = 1024 * 124
        node2.disk_total = 80
        node2.disk_used = 20
        node2.hostname = 'host2'
        node2.numa_topology = None
        node2.labels = {}
        node2.pci_device_pools = None
        node2.disk_quota_supported = True
        node3 = objects.ComputeNode(self.context)
        node3.cpus = 48
        node3.cpu_used = 0.0
        node3.mem_total = 1024 * 128
        node3.mem_used = 1024 * 4
        node3.mem_free = 1024 * 124
        node3.disk_total = 80
        node3.disk_used = 20
        node3.hostname = 'host3'
        node3.numa_topology = None
        node3.labels = {}
        node3.pci_device_pools = None
        node3.disk_quota_supported = True
        node4 = objects.ComputeNode(self.context)
        node4.cpus = 48
        node4.cpu_used = 0.0
        node4.mem_total = 1024 * 128
        node4.mem_used = 1024 * 4
        node4.mem_free = 1024 * 124
        node4.disk_total = 80
        node4.disk_used = 20
        node4.hostname = 'host4'
        node4.numa_topology = None
        node4.labels = {}
        node4.pci_device_pools = None
        node4.disk_quota_supported = True
        nodes = [node1, node2, node3, node4]
        mock_compute_list.return_value = nodes

        def side_effect(hosts):
            return hosts[2]
        mock_random_choice.side_effect = side_effect
        mock_service_is_up.return_value = True
        extra_spec = {}
        dests = self.driver.select_destinations(self.context, containers,
                                                extra_spec)

        self.assertEqual(1, len(dests))
        (host, node) = (dests[0]['host'], dests[0]['nodename'])
        self.assertEqual('host3', host)
        self.assertIsNone(node)

    @mock.patch.object(objects.ComputeNode, 'list')
    @mock.patch.object(objects.ZunService, 'list_by_binary')
    @mock.patch('random.choice')
    def test_select_destinations_no_valid_host(self, mock_random_choice,
                                               mock_list_by_binary,
                                               mock_compute_list):

        def _return_services(*args, **kwargs):
            return []

        self.driver.servicegroup_api.service_is_up = mock.Mock(
            return_value=True)
        mock_list_by_binary.side_effect = _return_services
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        extra_spec = {}
        self.assertRaises(exception.NoValidHost,
                          self.driver.select_destinations, self.context,
                          containers, extra_spec)
