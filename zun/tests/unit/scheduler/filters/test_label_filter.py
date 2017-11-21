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
from zun.scheduler.filters import label_filter
from zun.tests import base


class TestLabelFilter(base.TestCase):

    def setUp(self):
        super(TestLabelFilter, self).setUp()
        self.context = context.RequestContext('fake_user', 'fake_project')

    def test_label_filter_pass(self):
        self.filt_cls = label_filter.LabelFilter()
        container = objects.Container(self.context)
        container.name = 'test-container'
        extra_spec = {'hints': {'label:type': 'test'}}
        host = objects.ComputeNode(self.context)
        host.labels = {'type': 'test'}
        self.assertTrue(self.filt_cls.host_passes(host, container, extra_spec))

    def test_label_filter_fail(self):
        self.filt_cls = label_filter.LabelFilter()
        container = objects.Container(self.context)
        container.name = 'test-container'
        extra_spec = {'hints': {'label:type': 'test'}}
        host = objects.ComputeNode(self.context)
        host.labels = {'type': 'production'}
        self.assertFalse(self.filt_cls.host_passes(host, container,
                                                   extra_spec))
