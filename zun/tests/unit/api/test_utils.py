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

from zun.api import utils
from zun.common import exception
from zun.tests import base


class TestUtils(base.BaseTestCase):
    """Test cases for zun.api.utils"""

    def test_validate_limit(self):
        self.assertEqual(1000, utils.validate_limit(None))
        self.assertEqual(1000, utils.validate_limit(1001))
        self.assertEqual(50, utils.validate_limit(50))
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Limit must be positive"):
            utils.validate_limit(-1)
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Limit must be positive"):
            utils.validate_limit(0)
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Limit must be positive integer"):
            utils.validate_limit('a')
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Limit must be positive integer"):
            utils.validate_limit('5.5')

    def test_validate_sort_dir(self):
        self.assertEqual('asc', utils.validate_sort_dir('asc'))
        self.assertEqual('desc', utils.validate_sort_dir('desc'))
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Invalid sort direction"):
            utils.validate_sort_dir(None)
        with self.assertRaisesRegex(exception.InvalidValue,
                                    "Invalid sort direction"):
            utils.validate_sort_dir('abc')
