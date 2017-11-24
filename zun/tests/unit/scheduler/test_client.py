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

from oslo_config import cfg

from zun.scheduler import client as scheduler_client
from zun.scheduler import filter_scheduler
from zun.tests import base
from zun.tests.unit.scheduler import fakes


CONF = cfg.CONF


class SchedulerClientTestCase(base.TestCase):

    def setUp(self):
        super(SchedulerClientTestCase, self).setUp()
        self.client_cls = scheduler_client.SchedulerClient
        self.client = self.client_cls()

    def test_init_using_default_schedulerdriver(self):
        driver = self.client_cls().driver
        self.assertIsInstance(driver, filter_scheduler.FilterScheduler)

    def test_init_using_custom_schedulerdriver(self):
        CONF.set_override('driver', 'fake_scheduler', group='scheduler')
        driver = self.client_cls().driver
        self.assertIsInstance(driver, fakes.FakeScheduler)

    @mock.patch('zun.scheduler.filter_scheduler.FilterScheduler'
                '.select_destinations')
    def test_select_destinations(self, mock_select_destinations):
        fake_args = ['ctxt', 'fake_containers', 'fake_extra_spec']
        self.client.select_destinations(*fake_args)
        mock_select_destinations.assert_called_once_with(*fake_args)
