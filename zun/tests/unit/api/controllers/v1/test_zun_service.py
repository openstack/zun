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
from oslo_config import cfg

from zun.api import servicegroup
from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.api import utils as api_utils


class DbRec(object):

    def __init__(self, d):
        self.rec_as_dict = d

    def as_dict(self):
        return self.rec_as_dict


class TestZunServiceController(api_base.FunctionalTest):

    @mock.patch('zun.common.policy.enforce')
    def test_empty(self, mock_policy):
        mock_policy.return_value = True
        response = self.get_json('/services')
        self.assertEqual([], response['services'])

    def _rpc_api_reply(self, count=1, **kwarg):
        reclist = []
        for i in range(count):
            elem = api_utils.zservice_get_data(**kwarg)
            elem['id'] = i + 1
            rec = DbRec(elem)
            reclist.append(rec)
        return reclist

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_one(self, svc_up, mock_list, mock_policy):
        mock_policy.return_value = True
        mock_list.return_value = self._rpc_api_reply()
        svc_up.return_value = "up"

        response = self.get_json('/services')
        self.assertEqual(1, len(response['services']))
        self.assertEqual(1, response['services'][0]['id'])
        self.assertEqual('fake-zone',
                         response['services'][0]['availability_zone'])

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_get_many(self, svc_up, mock_list, mock_policy):
        mock_policy.return_value = True
        svc_num = 5
        mock_list.return_value = self._rpc_api_reply(svc_num)
        svc_up.return_value = "up"

        response = self.get_json('/services')
        self.assertEqual(len(response['services']), svc_num)
        for i in range(svc_num):
            elem = response['services'][i]
            self.assertEqual(elem['id'], i + 1)

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'list')
    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
    def test_default_availability_zone(self, svc_up, mock_list, mock_policy):
        cfg.CONF.set_override("default_availability_zone", "default-zone")
        mock_policy.return_value = True
        mock_list.return_value = self._rpc_api_reply(availability_zone=None)
        svc_up.return_value = "up"

        response = self.get_json('/services')
        self.assertEqual(1, len(response['services']))
        self.assertEqual(1, response['services'][0]['id'])
        self.assertEqual('default-zone',
                         response['services'][0]['availability_zone'])

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'get_by_host_and_binary')
    @mock.patch.object(objects.ZunService, 'update')
    def test_enable(self, mock_update, mock_get_host, mock_policy):
        mock_policy.return_value = True
        return_value = {
            'service': {
                'host': 'fake-host',
                'binary': 'fake-binary',
                'disabled': False,
                'disabled_reason': None
            },
        }
        params = {'binary': 'fake-binary', 'host': 'fake-host'}
        response = self.put_json('/services/enable', params)
        self.assertFalse(response.json['service']['disabled'])
        self.assertEqual(return_value, response.json)

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'get_by_host_and_binary')
    @mock.patch.object(objects.ZunService, 'update')
    def test_disable(self, mock_update, mock_get_host, mock_policy):
        mock_policy.return_value = True
        return_value = {
            'service': {
                'host': 'fake-host',
                'binary': 'fake-binary',
                'disabled': True,
                'disabled_reason': 'abc'
            },
        }
        params = {'binary': 'fake-binary', 'host': 'fake-host',
                  'disabled_reason': 'abc'}
        response = self.put_json('/services/disable', params)
        self.assertTrue(response.json['service']['disabled'])
        self.assertEqual('abc', response.json['service']['disabled_reason'])
        self.assertEqual(return_value, response.json)

    @mock.patch('zun.common.policy.enforce')
    @mock.patch.object(objects.ZunService, 'get_by_host_and_binary')
    @mock.patch.object(objects.ZunService, 'update')
    def test_force_down(self, mock_force_down, mock_get_host, mock_policy):
        mock_policy.return_value = True
        return_value = {
            'service': {
                'host': 'fake-host',
                'binary': 'fake-binary',
                'forced_down': True
            },
        }
        params = {'binary': 'fake-binary', 'host': 'fake-host',
                  'forced_down': True}
        response = self.put_json('/services/force_down', params)
        self.assertTrue(response.json['service']['forced_down'])
        self.assertEqual(return_value, response.json)


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
