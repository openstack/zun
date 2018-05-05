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

import mock
from mock import patch

from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestAvailabilityZoneController(api_base.FunctionalTest):

    @mock.patch('zun.common.policy.enforce')
    @patch('zun.objects.ZunService.list')
    def test_get_all_availability_zones(self,
                                        mock_availability_zone_list,
                                        mock_policy):
        mock_policy.return_value = True
        test_a_zone = utils.get_test_zun_service()
        availability_zones = [objects.ZunService(self.context, **test_a_zone)]
        mock_availability_zone_list.return_value = availability_zones

        response = self.get('/v1/availability_zones')

        mock_availability_zone_list.assert_called_once_with(
            mock.ANY, 1000, None, 'availability_zone', 'asc')
        self.assertEqual(200, response.status_int)
        actual_a_zones = response.json['availability_zones']
        self.assertEqual(1, len(actual_a_zones))
        self.assertEqual(test_a_zone['availability_zone'],
                         actual_a_zones[0].get('availability_zone'))


class TestAvailabilityZonetEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project_id:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'availability_zones:get_all', self.get_json, '/availability_zones',
            expect_errors=True)
