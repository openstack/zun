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
        self.assertEqual(None, types.Text.validate(None))

        self.assertEqual('test_value', types.Text.validate('test_value'))
        self.assertRaises(exception.InvalidValue,
                          types.Text.validate, 1)

    def test_string_type(self):
        self.assertEqual(None, types.String.validate(None))

        test_value = 'test_value'
        self.assertEqual(test_value, types.String.validate(test_value))
        self.assertRaises(exception.InvalidValue,
                          types.String.validate, 1)

        # test min_length
        for i in range(0, len(test_value)+1):
            self.assertEqual(test_value, types.String.validate(
                test_value, min_length=i))
        for i in range(len(test_value)+1, 20):
            self.assertRaises(exception.InvalidValue,
                              types.String.validate, test_value,
                              min_length=i)

        # test max_length
        for i in range(1, len(test_value)):
            self.assertRaises(exception.InvalidValue,
                              types.String.validate, test_value,
                              max_length=i)
        for i in range(len(test_value), 20):
            self.assertEqual(test_value, types.String.validate(
                test_value, max_length=i))

    def test_integer_type(self):
        self.assertEqual(None, types.Integer.validate(None))

        test_value = 10
        self.assertEqual(test_value, types.Integer.validate(test_value))
        self.assertEqual(test_value, types.Integer.validate('10'))
        self.assertRaises(exception.InvalidValue,
                          types.Integer.validate, 'invalid')
        self.assertRaises(exception.InvalidValue,
                          types.Integer.validate, '0.5')

        # test minimum
        for i in range(0, test_value+1):
            self.assertEqual(test_value, types.Integer.validate(
                test_value, minimum=i))
        for i in range(test_value+1, 20):
            self.assertRaises(exception.InvalidValue,
                              types.Integer.validate, test_value,
                              minimum=i)

        # test maximum
        for i in range(0, test_value):
            self.assertRaises(exception.InvalidValue,
                              types.Integer.validate, test_value,
                              maximum=i)
        for i in range(test_value, 20):
            self.assertEqual(test_value, types.Integer.validate(
                test_value, maximum=i))

    def test_port_type(self):
        self.assertEqual(None, types.Integer.validate(None))

        self.assertEqual(1, types.Port.validate('1'))
        self.assertEqual(80, types.Port.validate('80'))
        self.assertEqual(65535, types.Port.validate('65535'))
        self.assertRaises(exception.InvalidValue,
                          types.Port.validate, '0')
        self.assertRaises(exception.InvalidValue,
                          types.Port.validate, '-1')
        self.assertRaises(exception.InvalidValue,
                          types.Port.validate, '65536')

    def test_float_type(self):
        self.assertEqual(None, types.Float.validate(None))

        self.assertEqual(0.5, types.Float.validate('0.5'))
        self.assertEqual(1.0, types.Float.validate('1'))
        self.assertEqual(10.0, types.Float.validate('10'))
        self.assertRaises(exception.InvalidValue,
                          types.Float.validate, 'invalid')

    def test_bool_type(self):
        self.assertTrue(types.Bool.validate(None, default=True))

        test_value = True
        self.assertEqual(test_value, types.Bool.validate(True))
        self.assertEqual(test_value, types.Bool.validate('True'))
        self.assertEqual(test_value, types.Bool.validate('true'))
        self.assertEqual(test_value, types.Bool.validate('TRUE'))
        self.assertRaises(exception.InvalidValue,
                          types.Bool.validate, None)
        self.assertRaises(exception.InvalidValue,
                          types.Bool.validate, '')
        self.assertRaises(exception.InvalidValue,
                          types.Bool.validate, 'TTT')
        self.assertRaises(exception.InvalidValue,
                          types.Bool.validate, 2)

    def test_custom(self):
        class TestAPI(base.APIBase):
            fields = {
                'test': {
                    'validate': lambda v: v
                },
            }

        test_type = types.Custom(TestAPI)
        self.assertEqual(None, test_type.validate(None))

        value = TestAPI(test='test_value')
        value = test_type.validate(value)
        self.assertIsInstance(value, TestAPI)
        self.assertEqual({'test': 'test_value'}, value.as_dict())

        test_type = types.Custom(TestAPI)
        value = test_type.validate({'test': 'test_value'})
        self.assertIsInstance(value, TestAPI)
        self.assertEqual({'test': 'test_value'}, value.as_dict())

        self.assertRaises(
            exception.InvalidValue,
            test_type.validate, 'invalid_value')

    def test_list_with_text_type(self):
        list_type = types.List(types.Text)
        self.assertEqual(None, list_type.validate(None))

        value = list_type.validate(['test1', 'test2'])
        self.assertEqual(['test1', 'test2'], value)

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
        self.assertEqual(None, list_type.validate(None))

        value = [{'test': 'test_value'}]
        value = list_type.validate(value)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], TestAPI)
        self.assertEqual({'test': 'test_value'}, value[0].as_dict())

    def test_name_type(self):
        test_value = '***'
        self.assertRaises(exception.InvalidValue,
                          types.NameType.validate, test_value)

        test_value = '*' * 256
        self.assertRaises(exception.InvalidValue,
                          types.NameType.validate, test_value)

    def test_image_name_type(self):
        test_value = ""
        self.assertRaises(exception.InvalidValue,
                          types.ImageNameType.validate, test_value)

        test_value = '*' * 256
        self.assertRaises(exception.InvalidValue,
                          types.ImageNameType.validate, test_value)

    def test_container_memory_type(self):
        test_value = '4m'
        value = types.MemoryType.validate(test_value)
        self.assertEqual(value, test_value)

        test_value = '4'
        self.assertRaises(exception.InvalidValue,
                          types.MemoryType.validate, test_value)

        test_value = '10000A'
        self.assertRaises(exception.InvalidValue,
                          types.MemoryType.validate, test_value)

        test_value = '4K'
        self.assertRaises(exception.InvalidValue,
                          types.MemoryType.validate, test_value)

        test_value = '4194304'
        value = types.MemoryType.validate(test_value)
        self.assertEqual(value, test_value)

        test_value = '4194304.0'
        self.assertRaises(exception.InvalidValue,
                          types.MemoryType.validate, test_value)

    def test_image_size(self):
        test_value = '400'
        value = types.ImageSize.validate(test_value)
        self.assertEqual(value, test_value)

        test_value = '4194304.0'
        self.assertRaises(exception.InvalidValue,
                          types.ImageSize.validate, test_value)

        test_value = '10000A'
        self.assertRaises(exception.InvalidValue,
                          types.ImageSize.validate, test_value)

        test_value = '4K'
        expected_value = 4096
        value = types.ImageSize.validate(test_value)
        self.assertEqual(value, expected_value)
