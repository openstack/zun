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

from unittest import mock

from zun.tests.unit.api import base as api_base


class TestQuotaClassController(api_base.FunctionalTest):
    def setUp(self):
        super(TestQuotaClassController, self).setUp()
        self.default_quotas = {
            'containers': 40,
            'cpu': 20,
            'memory': 51200,
            'disk': 100
        }

    @mock.patch('zun.common.policy.enforce', return_value=True)
    def test_put_quota(self, mock_policy):
        update_quota_dicts = {
            'containers': '50',
            'memory': '61440'
        }

        admin_project_id = 'fakeadminprojectid'
        path = '/quota_classes/' + admin_project_id
        response = self.put_json(path, update_quota_dicts)
        self.assertEqual(200, response.status_int)
        self.assertEqual(50, response.json['containers'])
        self.assertEqual(61440, response.json['memory'])

    @mock.patch('zun.common.policy.enforce', return_value=True)
    def test_get_quota(self, mock_policy):
        admin_project_id = 'fakeadminprojectid'
        path = '/quota_classes/' + admin_project_id
        response = self.get(path)
        self.assertEqual(200, response.status_int)
        self.assertEqual(self.default_quotas, response.json)
