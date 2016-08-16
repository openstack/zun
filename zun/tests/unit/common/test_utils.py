#    Copyright 2016 IBM, Corp.
#
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

from zun.common import exception
from zun.common.utils import check_container_id
from zun.common.utils import translate_exception
from zun.tests import base


class TestUtils(base.BaseTestCase):
    """Test cases for zun.common.utils"""

    def test_check_container_id(self):

        @check_container_id
        def foo(self, container):
            pass

        fake_container = mock.MagicMock()
        fake_container.container_id = None

        self.assertRaises(exception.Invalid, foo,
                          self, fake_container)

    def test_translate_exception(self):

        @translate_exception
        def foo(self, context):
            raise TypeError()

        self.assertRaises(exception.ZunException, foo,
                          self, mock.MagicMock())
