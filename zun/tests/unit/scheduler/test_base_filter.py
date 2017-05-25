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
Tests for base filter
"""
import inspect

import mock

from zun.scheduler import base_filters
from zun.tests import base


class BaseFilterTestCase(base.TestCase):
    """Test case for base filter class."""

    @mock.patch('zun.scheduler.base_filters.BaseFilter._filter_one')
    def test_filter_all(self, mock_filter_one):
        mock_filter_one.side_effect = [True, False, True]
        filter_obj_list = ['obj1', 'obj2', 'obj3']
        container = {}
        base_filter = base_filters.BaseFilter()
        extra_spec = {}
        result = base_filter.filter_all(filter_obj_list, container, extra_spec)
        self.assertTrue(inspect.isgenerator(result))
        self.assertEqual(['obj1', 'obj3'], list(result))

    def test_run_filter_for_index(self):
        base_filter = base_filters.BaseFilter()
        base_filter.run_filter_once_per_request = False
        result = base_filter.run_filter_for_index(2)
        self.assertTrue(result)
