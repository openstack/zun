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

from oslo_utils import uuidutils

from zun import objects
from zun.objects import numa
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestHostController(api_base.FunctionalTest):

    @patch('zun.objects.ComputeNode.list')
    def test_get_all_hosts(self, mock_host_list):
        test_host = utils.get_test_compute_node()
        numat = numa.NUMATopology._from_dict(test_host['numa_topology'])
        test_host['numa_topology'] = numat
        hosts = [objects.ComputeNode(self.context, **test_host)]
        mock_host_list.return_value = hosts

        extra_environ = {'HTTP_ACCEPT': 'application/json'}
        headers = {'OpenStack-API-Version': 'container 1.4'}
        response = self.app.get('/v1/hosts', extra_environ=extra_environ,
                                headers=headers)

        mock_host_list.assert_called_once_with(mock.ANY,
                                               1000, None, 'hostname', 'asc',
                                               filters=None)
        self.assertEqual(200, response.status_int)
        actual_hosts = response.json['hosts']
        self.assertEqual(1, len(actual_hosts))
        self.assertEqual(test_host['uuid'],
                         actual_hosts[0].get('uuid'))

    @patch('zun.objects.ComputeNode.list')
    def test_get_all_hosts_with_pagination_marker(self, mock_host_list):
        host_list = []
        for id_ in range(4):
            test_host = utils.create_test_compute_node(
                context=self.context,
                uuid=uuidutils.generate_uuid())
            numat = numa.NUMATopology._from_dict(test_host['numa_topology'])
            test_host['numa_topology'] = numat
            host = objects.ComputeNode(self.context, **test_host)
            host_list.append(host)
        mock_host_list.return_value = host_list[-1:]
        extra_environ = {'HTTP_ACCEPT': 'application/json'}
        headers = {'OpenStack-API-Version': 'container 1.4'}
        response = self.app.get('/v1/hosts?limit=3&marker=%s'
                                % host_list[2].uuid,
                                extra_environ=extra_environ, headers=headers)

        self.assertEqual(200, response.status_int)
        actual_hosts = response.json['hosts']
        self.assertEqual(1, len(actual_hosts))
        self.assertEqual(host_list[-1].uuid,
                         actual_hosts[0].get('uuid'))

    @patch('zun.objects.ComputeNode.get_by_uuid')
    def test_get_one_host(self, mock_get_by_uuid):
        test_host = utils.get_test_compute_node()
        numat = numa.NUMATopology._from_dict(test_host['numa_topology'])
        test_host['numa_topology'] = numat
        test_host_obj = objects.ComputeNode(self.context, **test_host)
        mock_get_by_uuid.return_value = test_host_obj
        extra_environ = {'HTTP_ACCEPT': 'application/json'}
        headers = {'OpenStack-API-Version': 'container 1.4'}
        response = self.app.get('/v1/hosts/%s' % test_host['uuid'],
                                extra_environ=extra_environ,
                                headers=headers)
        mock_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_host['uuid'])
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_host['uuid'],
                         response.json['uuid'])


class TestHostEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project_id:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        extra_environ = {'HTTP_ACCEPT': 'application/json'}
        headers = {'OpenStack-API-Version': 'container 1.4'}
        self._common_policy_check(
            'host:get_all', self.get_json, '/hosts',
            expect_errors=True, extra_environ=extra_environ, headers=headers)

    def test_pollicy_disallow_get_one(self):
        extra_environ = {'HTTP_ACCEPT': 'application/json'}
        headers = {'OpenStack-API-Version': 'container 1.4'}
        self._common_policy_check(
            'host:get', self.get_json, '/hosts/%s' % '12345678',
            expect_errors=True, extra_environ=extra_environ, headers=headers)
