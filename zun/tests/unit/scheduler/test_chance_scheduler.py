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
from zun.scheduler import chance_scheduler
from zun.tests import base
from zun.tests.unit.db import utils


class ChanceSchedulerTestCase(base.TestCase):
    """Test case for Chance Scheduler."""

    driver_cls = chance_scheduler.ChanceScheduler

    @mock.patch.object(driver_cls, 'hosts_up')
    @mock.patch('random.choice')
    def test_select_destinations(self, mock_random_choice, mock_hosts_up):
        all_hosts = ['host1', 'host2', 'host3', 'host4']

        def _return_hosts(*args, **kwargs):
            return all_hosts

        mock_random_choice.side_effect = ['host3']
        mock_hosts_up.side_effect = _return_hosts

        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        extra_spec = {}
        dests = self.driver_cls().select_destinations(self.context, containers,
                                                      extra_spec)

        self.assertEqual(1, len(dests))
        (host, node) = (dests[0]['host'], dests[0]['nodename'])
        self.assertEqual('host3', host)
        self.assertIsNone(node)

        calls = [mock.call(all_hosts)]
        self.assertEqual(calls, mock_random_choice.call_args_list)

    @mock.patch.object(driver_cls, 'hosts_up')
    def test_select_destinations_no_valid_host(self, mock_hosts_up):

        def _return_no_host(*args, **kwargs):
            return []

        mock_hosts_up.side_effect = _return_no_host
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        extra_spec = {}
        self.assertRaises(exception.NoValidHost,
                          self.driver_cls().select_destinations, self.context,
                          containers, extra_spec)
