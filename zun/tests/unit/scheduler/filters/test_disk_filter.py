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
from zun.scheduler.filters import disk_filter
from zun.tests import base
from zun.tests.unit.scheduler import fakes


class TestDiskFilter(base.TestCase):

    def setUp(self):
        super(TestDiskFilter, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')

    def test_disk_filter_pass(self):
        self.filt_cls = disk_filter.DiskFilter()
        container = objects.Container(self.context)
        container.disk = 20
        host = fakes.FakeHostState('testhost')
        host.disk_total = 80
        host.disk_used = 40
        host.disk_quota_supported = True
        extra_spec = {}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))

    def test_disk_filter_pass_capsule(self):
        self.filt_cls = disk_filter.DiskFilter()
        capsule = objects.Capsule(self.context)
        host = fakes.FakeHostState('testhost')
        host.disk_total = 80
        host.disk_used = 40
        host.disk_quota_supported = True
        extra_spec = {}
        self.assertTrue(self.filt_cls.host_passes(host, capsule, extra_spec))

    def test_disk_filter_fail_not_enough_disk(self):
        self.filt_cls = disk_filter.DiskFilter()
        container = objects.Container(self.context)
        container.disk = 20
        host = fakes.FakeHostState('testhost')
        host.disk_total = 80
        host.disk_used = 70
        host.disk_quota_supported = True
        extra_spec = {}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))

    def test_disk_filter_fail_not_supported(self):
        self.filt_cls = disk_filter.DiskFilter()
        container = objects.Container(self.context)
        container.disk = 20
        host = fakes.FakeHostState('testhost')
        host.disk_total = 80
        host.disk_used = 40
        host.disk_quota_supported = False
        extra_spec = {}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))
