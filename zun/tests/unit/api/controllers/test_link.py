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

import collections
import six

from zun.api.controllers import link as link_module
from zun.tests import base as test_base


class TestLink(test_base.BaseTestCase):

    def test_make_link(self):
        link = link_module.make_link(
            'self', 'http://localhost:8080', 'v1', '',
            bookmark=True)

        ordered_link = collections.OrderedDict(sorted(link.items()))
        expected_value = collections.OrderedDict([
            ('href', 'http://localhost:8080/v1/'),
            ('rel', 'self')
        ])
        self.assertEqual(six.text_type(expected_value),
                         six.text_type(ordered_link))
