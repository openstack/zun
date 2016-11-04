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

from zun.api.controllers.v1 import zun_services as zservice
from zun.api import servicegroup
from zun import objects
from zun.tests import base
from zun.tests.unit.api import base as api_base
from zun.tests.unit.api import utils as api_utils


class TestZunServiceObject(base.BaseTestCase):

    def setUp(self):
        super(TestZunServiceObject, self).setUp()
        self.rpc_dict = api_utils.zservice_get_data()

    def test_msvc_obj_fields_filtering(self):
        """Test that it does filtering fields """
        self.rpc_dict['fake-key'] = 'fake-value'
        msvco = zservice.ZunService("up", **self.rpc_dict)
        self.assertNotIn('fake-key', msvco.fields)


class db_rec(object):

    def __init__(self, d):
        self.rec_as_dict = d

    def as_dict(self):
        return self.rec_as_dict


class TestZunServiceController(api_base.FunctionalTest):

    def test_empty(self):
        response = self.get_json('/services')
        self.assertEqual([], response['services'])

    def _rpc_api_reply(self, count=1):
        reclist = []
        for i in range(count):
            elem = api_utils.zservice_get_data()
            elem['id'] = i + 1
            rec = db_rec(elem)
            reclist.append(rec)
        return reclist

    @mock.patch.object(objects.ZunService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_one(self, svc_up, mock_list):
        mock_list.return_value = self._rpc_api_reply()
        svc_up.return_value = "up"

        response = self.get_json('/services')
        self.assertEqual(len(response['services']), 1)
        self.assertEqual(response['services'][0]['id'], 1)

    @mock.patch.object(objects.ZunService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_many(self, svc_up, mock_list):
        svc_num = 5
        mock_list.return_value = self._rpc_api_reply(svc_num)
        svc_up.return_value = "up"

        response = self.get_json('/services')
        self.assertEqual(len(response['services']), svc_num)
        for i in range(svc_num):
            elem = response['services'][i]
            self.assertEqual(elem['id'], i + 1)


class TestZunServiceEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'zun-service:get_all', self.get_json,
            '/services', expect_errors=True)
