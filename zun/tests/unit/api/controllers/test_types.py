# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from zun.api.controllers import base
from zun.api.controllers import types
from zun.common import exception
from zun.tests import base as test_base


class TestTypes(test_base.BaseTestCase):

    def test_text(self):
        self.assertEqual('test_value', types.Text.validate('test_value'))

    def test_custom(self):
        class TestAPI(base.APIBase):
            fields = {
                'test': {
                    'validate': lambda v: v
                },
            }

        test_type = types.Custom(TestAPI)
        value = TestAPI(test='test_value')
        value = test_type.validate(value)
        self.assertIsInstance(value, TestAPI)
        self.assertEqual(value.as_dict(), {'test': 'test_value'})

        test_type = types.Custom(TestAPI)
        value = test_type.validate({'test': 'test_value'})
        self.assertIsInstance(value, TestAPI)
        self.assertEqual(value.as_dict(), {'test': 'test_value'})

        self.assertRaises(
            exception.InvalidValue,
            test_type.validate, 'invalid_value')

    def test_list_with_text_type(self):
        list_type = types.List(types.Text)
        value = list_type.validate(['test1', 'test2'])
        self.assertEqual(value, ['test1', 'test2'])

        self.assertRaises(
            exception.InvalidValue,
            list_type.validate, 'invalid_value')

    def test_list_with_custom_type(self):
        class TestAPI(base.APIBase):
            fields = {
                'test': {
                    'validate': lambda v: v
                },
            }

        list_type = types.List(types.Custom(TestAPI))
        value = [{'test': 'test_value'}]
        value = list_type.validate(value)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], TestAPI)
        self.assertEqual(value[0].as_dict(), {'test': 'test_value'})
