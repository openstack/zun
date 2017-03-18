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

from zun.common import exception
from zun import objects
from zun.scheduler import filter_scheduler
from zun.tests import base
from zun.tests.unit.db import utils


class FakeService(object):

    def __init__(self, name, host):
        self.name = name
        self.host = host


class FilterSchedulerTestCase(base.TestCase):
    """Test case for Filter Scheduler."""

    driver_cls = filter_scheduler.FilterScheduler

    def setUp(self):
        super(FilterSchedulerTestCase, self).setUp()
        self.driver = self.driver_cls()

    @mock.patch.object(objects.ZunService, 'list_by_binary')
    @mock.patch('random.choice')
    def test_select_destinations(self, mock_random_choice,
                                 mock_list_by_binary):
        all_services = [FakeService('service1', 'host1'),
                        FakeService('service2', 'host2'),
                        FakeService('service3', 'host3'),
                        FakeService('service4', 'host4')]
        all_hosts = ['host1', 'host2', 'host3', 'host4']

        def _return_services(*args, **kwargs):
            return all_services

        mock_random_choice.side_effect = ['host3']
        self.driver.servicegroup_api.service_is_up = mock.Mock(
            return_value=True)
        mock_list_by_binary.side_effect = _return_services
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        dests = self.driver.select_destinations(self.context, containers)

        self.assertEqual(1, len(dests))
        (host, node) = (dests[0]['host'], dests[0]['nodename'])
        self.assertEqual('host3', host)
        self.assertIsNone(node)

        calls = [mock.call(all_hosts)]
        self.assertEqual(calls, mock_random_choice.call_args_list)

    @mock.patch.object(objects.ZunService, 'list_by_binary')
    @mock.patch('random.choice')
    def test_select_destinations_no_valid_host(self, mock_random_choice,
                                               mock_list_by_binary):

        def _return_services(*args, **kwargs):
            return []

        self.driver.servicegroup_api.service_is_up = mock.Mock(
            return_value=True)
        mock_list_by_binary.side_effect = _return_services
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        self.assertRaises(exception.NoValidHost,
                          self.driver.select_destinations, self.context,
                          containers)
