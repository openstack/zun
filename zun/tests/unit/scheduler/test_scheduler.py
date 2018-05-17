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
"""
Tests For Scheduler
"""

import mock

from zun import objects
from zun.tests import base
from zun.tests.unit.scheduler import fakes


class SchedulerTestCase(base.TestCase):
    """Test case for base scheduler driver class."""

    driver_cls = fakes.FakeScheduler

    def setUp(self):
        super(SchedulerTestCase, self).setUp()
        self.driver = self.driver_cls()

    @mock.patch('zun.objects.ZunService.list_by_binary')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    def test_hosts_up(self, mock_service_is_up, mock_list_by_binary):
        service1 = objects.ZunService()
        service2 = objects.ZunService()
        service1.host = 'host1'
        service1.disabled = False
        service2.host = 'host2'
        service2.disabled = False
        services = [service1, service2]

        mock_list_by_binary.return_value = services
        mock_service_is_up.side_effect = [False, True]

        result = self.driver.hosts_up(self.context)
        self.assertEqual(['host2'], result)

        mock_list_by_binary.assert_called_once_with(self.context,
                                                    'zun-compute')
        calls = [mock.call(service1), mock.call(service2)]
        self.assertEqual(calls, mock_service_is_up.call_args_list)
