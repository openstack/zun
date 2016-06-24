# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import collections
import six

from zun.api.controllers import base
from zun.tests import base as test_base


class TestAPIBase(test_base.BaseTestCase):

    def setUp(self):
        super(TestAPIBase, self).setUp()

        class TestAPI(base.APIBase):
            fields = {
                'test': {
                    'validate': lambda v: v
                },
            }

        self.test_api_cls = TestAPI

    def test_assign_field(self):
        test_api = self.test_api_cls()
        test_api.test = 'test_value'

        expected_value = {
            'test': 'test_value',
        }
        self.assertEqual(expected_value, test_api.__json__())

    def test_no_field_assigned(self):
        test_api = self.test_api_cls()
        expected_value = {}
        self.assertEqual(expected_value, test_api.__json__())

    def test_assign_field_in_constructor(self):
        test_api = self.test_api_cls(test='test_value')
        expected_value = {
            'test': 'test_value',
        }
        self.assertEqual(expected_value, test_api.__json__())

    def test_assign_nonexist_field(self):
        test_api = self.test_api_cls()
        test_api.nonexist = 'test_value'

        expected_value = {}
        self.assertEqual(expected_value, test_api.__json__())

    def test_assign_multiple_fields(self):
        class TestAPI(base.APIBase):
            fields = {
                'test': {
                    'validate': lambda v: v
                },
                'test2': {
                    'validate': lambda v: v
                },
            }

        test_api = TestAPI()
        test_api.test = 'test_value'
        test_api.test2 = 'test_value2'
        test_api.test3 = 'test_value3'

        expected_value = collections.OrderedDict([
            ('test', 'test_value'),
            ('test2', 'test_value2'),
        ])
        actual_value = collections.OrderedDict(
            sorted(test_api.as_dict().items()))
        self.assertEqual(six.text_type(expected_value),
                         six.text_type(actual_value))
