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

from tempest.lib import decorators

from zun.tests.tempest import base


class TestBasic(base.BaseZunTest):

    @decorators.idempotent_id('a04f61f2-15ae-4200-83b7-1f311b101f65')
    def test_basic(self):
        # This is a basic test used to verify zun tempest plugin
        # works. Remove it after real test cases being added.
        pass
