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

from zun import objects
from zun.pci import stats
from zun.scheduler.filters import pci_passthrough_filter
from zun.scheduler.host_state import HostState
from zun.tests import base


class TestPCIPassthroughFilter(base.TestCase):

    def setUp(self):
        super(TestPCIPassthroughFilter, self).setUp()
        self.filt_cls = pci_passthrough_filter.PciPassthroughFilter()

    def test_pci_passthrough_pass(self):
        pci_stats_mock = mock.MagicMock()
        pci_stats_mock.support_requests.return_value = True
        request = objects.ContainerPCIRequest(
            count=1, spec=[{'vendor_id': '8086'}])
        requests = objects.ContainerPCIRequests(requests=[request])
        container = objects.Container(self.context)
        host = HostState('testhost')
        host.pci_stats = pci_stats_mock
        extra_spec = {'pci_requests': requests}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))
        pci_stats_mock.support_requests.assert_called_once_with(
            requests.requests)

    def test_pci_passthrough_fail(self):
        pci_stats_mock = mock.MagicMock()
        pci_stats_mock.support_requests.return_value = False
        request = objects.ContainerPCIRequest(
            count=1, spec=[{'vendor_id': '8086'}])
        requests = objects.ContainerPCIRequests(requests=[request])
        container = objects.Container(self.context)
        host = HostState('testhost')
        host.pci_stats = pci_stats_mock
        extra_spec = {'pci_requests': requests}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))
        pci_stats_mock.support_requests.assert_called_once_with(
            requests.requests)

    def test_pci_passthrough_no_pci_request(self):
        container = objects.Container(self.context)
        host = HostState('testhost')
        extra_spec = {'pci_requests': None}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))

    def test_pci_passthrough_empty_pci_request_obj(self):
        requests = objects.ContainerPCIRequests(requests=[])
        container = objects.Container(self.context)
        host = HostState('testhost')
        extra_spec = {'pci_requests': requests}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))

    def test_pci_passthrough_no_pci_stats(self):
        request = objects.ContainerPCIRequest(
            count=1, spec=[{'vendor_id': '8086'}])
        requests = objects.ContainerPCIRequests(requests=[request])
        container = objects.Container(self.context)
        host = HostState('testhost')
        host.pci_stats = stats.PciDeviceStats()
        extra_spec = {'pci_requests': requests}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))

    def test_pci_passthrough_with_pci_stats_none(self):
        request = objects.ContainerPCIRequest(
            count=1, spec=[{'vendor_id': '8086'}])
        requests = objects.ContainerPCIRequests(requests=[request])
        container = objects.Container(self.context)
        host = HostState('testhost')
        host.pci_stats = None
        extra_spec = {'pci_requests': requests}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))
