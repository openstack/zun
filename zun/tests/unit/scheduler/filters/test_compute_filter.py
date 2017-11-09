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
from oslo_utils import timeutils

from zun.common import context
from zun import objects
from zun.scheduler.filters import compute_filter
from zun.tests import base
from zun.tests.unit.scheduler import fakes


@mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
class TestComputeFilter(base.TestCase):

    def setUp(self):
        super(TestComputeFilter, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')

    def test_compute_filter_manual_disable(self, service_up_mock):
        filt_cls = compute_filter.ComputeFilter()
        container = objects.Container(self.context)
        extra_spec = {}
        service = objects.ZunService(self.context)
        service.disabled = True
        service.disabled_reason = 'This is a reason!'
        host = fakes.FakeHostState('host1',
                                   {'service': service})
        self.assertFalse(filt_cls.host_passes(host, container,
                                              extra_spec))
        self.assertFalse(service_up_mock.called)

    def test_compute_filter_sgapi_passes(self, service_up_mock):
        filt_cls = compute_filter.ComputeFilter()
        container = objects.Container(self.context)
        service = objects.ZunService(self.context)
        service.disabled = False
        extra_spec = {}
        host = fakes.FakeHostState('host2',
                                   {'service': service})
        service_up_mock.return_value = True
        self.assertTrue(filt_cls.host_passes(host, container,
                                             extra_spec))
        service_up_mock.assert_called_once_with(service)

    def test_compute_filter_sgapi_fails(self, service_up_mock):
        filts_cls = compute_filter.ComputeFilter()
        container = objects.Container(self.context)
        service = objects.ZunService(self.context)
        service.disabled = False
        service.updated_at = timeutils.utcnow()
        extra_spec = {}
        host = fakes.FakeHostState('host3',
                                   {'service': service})
        service_up_mock.return_value = False
        self.assertFalse(filts_cls.host_passes(host, container,
                                               extra_spec))
        service_up_mock.assert_called_once_with(service)
