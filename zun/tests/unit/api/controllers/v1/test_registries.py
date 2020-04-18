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
from unittest.mock import patch

from oslo_utils import uuidutils
from webtest.app import AppError

from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils
from zun.tests.unit.objects import utils as obj_utils


class TestRegistryController(api_base.FunctionalTest):

    def test_create_registry(self):
        params = ('{"registry": {"name": "MyRegistry", "domain": "test.io",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(201, response.status_int)
        self.assertEqual(1, len(response.json))
        r = response.json['registry']
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertEqual('MyRegistry', r.get('name'))
        self.assertEqual('test.io', r.get('domain'))
        self.assertEqual('fake-user', r.get('username'))
        self.assertEqual('***', r.get('password'))

    def test_create_registry_domain_not_specified(self):
        params = ('{"registry": {"name": "MyRegistry",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        with self.assertRaisesRegex(AppError,
                                    "is a required property"):
            self.post('/v1/registries/',
                      params=params,
                      content_type='application/json')

    def test_create_registry_with_minimum_params(self):
        params = ('{"registry": {"domain": "test.io"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(201, response.status_int)
        self.assertEqual(1, len(response.json))
        r = response.json['registry']
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertIsNone(r.get('name'))
        self.assertEqual('test.io', r.get('domain'))
        self.assertIsNone(r.get('username'))
        self.assertEqual('***', r.get('password'))

    def test_create_registry_invalid_long_name(self):
        # Long name
        params = ('{"registry": {"name": "' + 'i' * 256 + '",'
                  '"domain": "test.io","username": "fake-user",'
                  '"password": "fake-pass"}}')
        self.assertRaises(AppError, self.post, '/v1/registries/',
                          params=params, content_type='application/json')

    def test_get_all_registries(self):
        params = ('{"registry": {"name": "MyRegistry", "domain": "test.io",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(201, response.status_int)
        response = self.get('/v1/registries/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        r = response.json['registries'][0]
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertEqual('MyRegistry', r.get('name'))
        self.assertEqual('test.io', r.get('domain'))
        self.assertEqual('fake-user', r.get('username'))
        self.assertEqual('***', r.get('password'))

    @patch('zun.common.policy.enforce')
    @patch('zun.objects.Registry.list')
    def test_get_all_registries_all_projects(self, mock_registry_list,
                                             mock_policy):
        mock_policy.return_value = True
        test_registry = utils.get_test_registry()
        registries = [objects.Registry(self.context, **test_registry)]
        mock_registry_list.return_value = registries

        response = self.get('/v1/registries/?all_projects=1')

        mock_registry_list.assert_called_once_with(mock.ANY,
                                                   1000, None, 'id', 'asc',
                                                   filters={})
        context = mock_registry_list.call_args[0][0]
        self.assertIs(True, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_registries = response.json['registries']
        self.assertEqual(1, len(actual_registries))
        self.assertEqual(test_registry['uuid'],
                         actual_registries[0].get('uuid'))

    @patch('zun.objects.Registry.list')
    def test_get_all_registries_with_pagination_marker(self,
                                                       mock_registry_list):
        registry_list = []
        for id_ in range(4):
            test_registry = utils.create_test_registry(
                id=id_, uuid=uuidutils.generate_uuid(),
                name='registry' + str(id_), context=self.context)
            registry_list.append(objects.Registry(self.context,
                                                  **test_registry))
        mock_registry_list.return_value = registry_list[-1:]
        response = self.get('/v1/registries/?limit=3&marker=%s'
                            % registry_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_registries = response.json['registries']
        self.assertEqual(1, len(actual_registries))
        self.assertEqual(registry_list[-1].uuid,
                         actual_registries[0].get('uuid'))

    @patch('zun.objects.Registry.list')
    def test_get_all_registries_with_filter(self, mock_registry_list):
        test_registry = utils.get_test_registry()
        registries = [objects.Registry(self.context, **test_registry)]
        mock_registry_list.return_value = registries

        response = self.get('/v1/registries/?name=fake-name')

        mock_registry_list.assert_called_once_with(
            mock.ANY, 1000, None, 'id', 'asc', filters={'name': 'fake-name'})
        self.assertEqual(200, response.status_int)
        actual_registries = response.json['registries']
        self.assertEqual(1, len(actual_registries))
        self.assertEqual(test_registry['uuid'],
                         actual_registries[0].get('uuid'))

    @patch('zun.objects.Registry.list')
    def test_get_all_registries_with_unknown_parameter(
            self, mock_registry_list):
        test_registry = utils.get_test_registry()
        registries = [objects.Registry(self.context, **test_registry)]
        mock_registry_list.return_value = registries

        response = self.get('/v1/registries/?unknown=fake-name',
                            expect_errors=True)

        mock_registry_list.assert_not_called()
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual("Unknown parameters: unknown",
                         response.json['errors'][0]['detail'])

    def test_get_one(self):
        params = ('{"registry": {"name": "MyRegistry", "domain": "test.io",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(201, response.status_int)
        # get by uuid
        registry_uuid = response.json['registry']['uuid']
        response = self.get('/v1/registries/%s/' % registry_uuid)
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        r = response.json['registry']
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertEqual('MyRegistry', r.get('name'))
        self.assertEqual('test.io', r.get('domain'))
        self.assertEqual('fake-user', r.get('username'))
        self.assertEqual('***', r.get('password'))
        # get by name
        registry_name = response.json['registry']['name']
        response = self.get('/v1/registries/%s/' % registry_name)
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        r = response.json['registry']
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertEqual('MyRegistry', r.get('name'))
        self.assertEqual('test.io', r.get('domain'))
        self.assertEqual('fake-user', r.get('username'))
        self.assertEqual('***', r.get('password'))

    def test_get_one_not_found(self):
        response = self.get('/v1/registries/%s/' % 'not-exist',
                            expect_errors=True)

        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual("Registry not-exist could not be found.",
                         response.json['errors'][0]['detail'])

    def test_patch_by_uuid(self):
        params = ('{"registry": {"name": "MyRegistry", "domain": "test.io",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(201, response.status_int)
        registry_uuid = response.json['registry']['uuid']
        params = {'registry': {'name': 'new-name', 'domain': 'new-domain',
                  'username': 'new-username', 'password': 'new-pass'}}
        response = self.patch_json(
            '/registries/%s/' % registry_uuid,
            params=params)
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        r = response.json['registry']
        self.assertIsNotNone(r.get('uuid'))
        self.assertIsNotNone(r.get('user_id'))
        self.assertIsNotNone(r.get('project_id'))
        self.assertEqual('new-name', r.get('name'))
        self.assertEqual('new-domain', r.get('domain'))
        self.assertEqual('new-username', r.get('username'))
        self.assertEqual('***', r.get('password'))

    def test_delete_registry_by_uuid(self):
        params = ('{"registry": {"name": "MyRegistry", "domain": "test.io",'
                  '"username": "fake-user", "password": "fake-pass"}}')
        response = self.post('/v1/registries/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(201, response.status_int)
        registry_uuid = response.json['registry']['uuid']
        response = self.delete('/v1/registries/%s/' % registry_uuid)
        self.assertEqual(204, response.status_int)
        response = self.get('/v1/registries/%s/' % registry_uuid,
                            expect_errors=True)
        self.assertEqual(404, response.status_int)


class TestRegistryEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        rules = dict({rule: 'project_id:non_fake'},
                     **kwarg.pop('bypass_rules', {}))
        self.policy.set_rules(rules)
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'registry:get_all', self.get, '/v1/registries/',
            expect_errors=True)

    def test_policy_disallow_get_all_all_projects(self):
        self._common_policy_check(
            'registry:get_all_all_projects',
            self.get, '/v1/registries/?all_projects=1',
            expect_errors=True,
            bypass_rules={'registry:get_all': 'project_id:fake_project'})

    def test_policy_disallow_get_one(self):
        registry = obj_utils.create_test_registry(self.context)
        self._common_policy_check(
            'registry:get_one', self.get,
            '/v1/registries/%s/' % registry.uuid,
            expect_errors=True)

    def test_policy_disallow_update(self):
        registry = obj_utils.create_test_registry(self.context)
        params = {'registry': {'name': 'newname'}}
        self._common_policy_check(
            'registry:update', self.patch_json,
            '/registries/%s/' % registry.uuid, params,
            expect_errors=True)

    def test_policy_disallow_create(self):
        params = ('{"registry": {"domain": "test.io"}}')
        self._common_policy_check(
            'registry:create', self.post, '/v1/registries/',
            params=params,
            content_type='application/json',
            expect_errors=True)

    def test_policy_disallow_delete(self):
        registry = obj_utils.create_test_registry(self.context)
        self._common_policy_check(
            'registry:delete', self.delete,
            '/v1/registries/%s/' % registry.uuid,
            expect_errors=True)

    def _owner_check(self, rule, func, *args, **kwargs):
        self.policy.set_rules({rule: "user_id:%(user_id)s"})
        response = func(*args, **kwargs)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_only_owner_get_one(self):
        registry = obj_utils.create_test_registry(self.context,
                                                  user_id='another')
        self._owner_check("registry:get_one", self.get_json,
                          '/registries/%s/' % registry.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        registry = obj_utils.create_test_registry(self.context,
                                                  user_id='another')
        self._owner_check(
            "registry:update", self.patch_json,
            '/registries/%s/' % registry.uuid,
            {'registry': {'name': 'newname'}},
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        registry = obj_utils.create_test_registry(self.context,
                                                  user_id='another')
        self._owner_check(
            "registry:delete", self.delete,
            '/registries/%s/' % registry.uuid,
            expect_errors=True)
