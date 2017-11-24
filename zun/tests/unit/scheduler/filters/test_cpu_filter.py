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

from zun.common import context
from zun import objects
from zun.scheduler.filters import cpu_filter
from zun.tests import base
from zun.tests.unit.scheduler import fakes


class TestCPUFilter(base.TestCase):

    def setUp(self):
        super(TestCPUFilter, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')

    def test_cpu_filter_pass(self):
        self.filt_cls = cpu_filter.CPUFilter()
        container = objects.Container(self.context)
        container.cpu = 5.0
        host = fakes.FakeHostState('testhost')
        host.cpus = 8
        host.cpu_used = 0.0
        extra_spec = {}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))

    def test_cpu_filter_fail(self):
        self.filt_cls = cpu_filter.CPUFilter()
        container = objects.Container(self.context)
        container.cpu = 8.0
        host = fakes.FakeHostState('testhost')
        host.cpus = 5
        host.cpu_used = 2.0
        extra_spec = {}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))
