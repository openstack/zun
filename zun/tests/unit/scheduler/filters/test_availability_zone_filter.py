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

from oslo_config import cfg

from zun.common import context
from zun import objects
from zun.scheduler.filters import availability_zone_filter as az_filter
from zun.tests import base
from zun.tests.unit.scheduler import fakes


class TestAvailabilityZoneFilter(base.TestCase):

    def setUp(self):
        super(TestAvailabilityZoneFilter, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')

    def test_az_filter(self):
        self.assertIs(True,
                      self._test_az_filter(request_az='test-az',
                                           node_az='test-az'))
        self.assertIs(False,
                      self._test_az_filter(request_az='test-az',
                                           node_az='another-az'))

    def test_az_filter_default_az(self):
        cfg.CONF.set_override("default_availability_zone", "default-az")
        self.assertIs(True,
                      self._test_az_filter(request_az='default-az',
                                           node_az=None))
        self.assertIs(False,
                      self._test_az_filter(request_az='another-az',
                                           node_az=None))

    def test_az_filter_default_schedule_az(self):
        cfg.CONF.set_override("default_schedule_zone", "schedule-az")
        self.assertIs(True,
                      self._test_az_filter(request_az=None,
                                           node_az='schedule-az'))
        self.assertIs(False,
                      self._test_az_filter(request_az=None,
                                           node_az='another-az'))

    def test_az_filter_no_az_requested(self):
        self.assertIs(True,
                      self._test_az_filter(request_az=None,
                                           node_az=None))
        self.assertIs(True,
                      self._test_az_filter(request_az=None,
                                           node_az='any-az'))

    def _test_az_filter(self, request_az, node_az):
        filt_cls = az_filter.AvailabilityZoneFilter()
        container = objects.Container(self.context)
        service = objects.ZunService(self.context)
        service.availability_zone = node_az
        extra_spec = {}
        if request_az:
            extra_spec = {'availability_zone': request_az}
        host = fakes.FakeHostState('fake-host',
                                   {'service': service})
        return filt_cls.host_passes(host, container, extra_spec)
