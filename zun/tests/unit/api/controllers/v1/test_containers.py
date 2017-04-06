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
from webtest.app import AppError

from oslo_utils import uuidutils

from zun.common import exception
from zun import objects
from zun.objects import fields
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils
from zun.tests.unit.objects import utils as obj_utils


class TestContainerController(api_base.FunctionalTest):
    @patch('zun.compute.api.API.container_run')
    @patch('zun.compute.api.API.image_search')
    def test_run_container(self, mock_search, mock_container_run):
        mock_container_run.side_effect = lambda x, y: y

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers?run=true',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_run.called)

    @patch('zun.compute.api.API.container_run')
    @patch('zun.compute.api.API.image_search')
    def test_run_container_wrong_run_value(self, mock_search,
                                           mock_container_run):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegexp(AppError,
                                     "Invalid input for query parameters"):
            self.app.post('/v1/containers?run=xyz', params=params,
                          content_type='application/json')

    @patch('zun.compute.rpcapi.API.container_run')
    @patch('zun.compute.rpcapi.API.image_search')
    def test_run_container_with_false(self, mock_search,
                                      mock_container_run):
        mock_container_run.side_effect = lambda x, y: y

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers?run=false',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        self.assertFalse(mock_container_run.called)

    @patch('zun.compute.rpcapi.API.container_run')
    @patch('zun.compute.rpcapi.API.image_search')
    def test_run_container_with_wrong(self, mock_search,
                                      mock_container_run):
        mock_container_run.side_effect = exception.InvalidValue
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        self.assertRaises(AppError, self.app.post, '/v1/containers?run=wrong',
                          params=params, content_type='application/json')
        self.assertTrue(mock_container_run.not_called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container(self, mock_search, mock_container_create):
        mock_container_create.side_effect = lambda x, y: y

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    def test_create_container_image_not_specified(self, mock_container_create):

        params = ('{"name": "MyDocker",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegexp(AppError,
                                     "is a required property"):
            self.app.post('/v1/containers/',
                          params=params,
                          content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_image_not_found(self, mock_search,
                                              mock_container_create):
        mock_container_create.side_effect = lambda x, y: y
        mock_search.side_effect = exception.ImageNotFound()

        params = {"name": "MyDocker", "image": "not-found"}
        response = self.post_json('/containers/', params, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_int)
        self.assertFalse(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_set_project_id_and_user_id(
            self, mock_search, mock_container_create):
        def _create_side_effect(cnxt, container):
            self.assertEqual(self.context.project_id, container.project_id)
            self.assertEqual(self.context.user_id, container.user_id)
            return container
        mock_container_create.side_effect = _create_side_effect

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        self.app.post('/v1/containers/',
                      params=params,
                      content_type='application/json')

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_resp_has_status_reason(self, mock_search,
                                                     mock_container_create):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        self.assertIn('status_reason', response.json.keys())

    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_command(self, mock_search,
                                           mock_container_delete,
                                           mock_container_create,
                                           mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({"key1": "val1", "key2": "val2"},
                         c.get('environment'))
        # Delete the container we created
        response = self.app.delete(
            '/v1/containers/%s?force=True' % c.get('uuid'))
        self.assertEqual(204, response.status_int)

        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        c = response.json['containers']
        self.assertEqual(0, len(c))
        self.assertTrue(mock_container_create.called)

    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_without_memory(self, mock_search,
                                             mock_container_create,
                                             mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertIsNone(c.get('memory'))
        self.assertEqual({"key1": "val1", "key2": "val2"},
                         c.get('environment'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_without_environment(self, mock_search,
                                                  mock_container_create,
                                                  mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512"}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({}, c.get('environment'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_without_name(self, mock_search,
                                           mock_container_create,
                                           mock_container_show):
        # No name param
        mock_container_create.side_effect = lambda x, y: y
        params = ('{"image": "ubuntu", "command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertIsNotNone(c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({"key1": "val1", "key2": "val2"},
                         c.get('environment'))

    @patch('zun.compute.rpcapi.API.container_show')
    @patch('zun.compute.rpcapi.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_no_retry_0(
            self,
            mock_search,
            mock_container_create,
            mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"restart_policy": {"Name": "no",'
                  '"MaximumRetryCount": "0"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({"Name": "no", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))

    @patch('zun.compute.rpcapi.API.container_show')
    @patch('zun.compute.rpcapi.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_no_retry_6(
            self,
            mock_search,
            mock_container_create,
            mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"restart_policy": {"Name": "no",'
                  '"MaximumRetryCount": "6"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({"Name": "no", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))

    @patch('zun.compute.rpcapi.API.container_show')
    @patch('zun.compute.rpcapi.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_unless_stopped(
            self,
            mock_search,
            mock_container_create,
            mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"restart_policy": {"Name": "unless-stopped",'
                  '"MaximumRetryCount": "0"}}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Stopped'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(1, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual('env', c.get('command'))
        self.assertEqual('Stopped', c.get('status'))
        self.assertEqual('512M', c.get('memory'))
        self.assertEqual({"Name": "unless-stopped", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))

    @patch('zun.compute.rpcapi.API.container_show')
    @patch('zun.compute.rpcapi.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_always_and_retrycount(
            self,
            mock_search,
            mock_container_create,
            mock_container_show):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"restart_policy": {"Name": "always",'
                  '"MaximumRetryCount": "1"}}')
        with self.assertRaisesRegexp(
                AppError, "maximum retry count not valid with"):
            self.app.post('/v1/containers/',
                          params=params,
                          content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.compute.rpcapi.API.container_create')
    @patch('zun.compute.rpcapi.API.image_search')
    def test_create_container_invalid_long_name(self, mock_search,
                                                mock_container_create):
        # Long name
        params = ('{"name": "' + 'i' * 256 + '", "image": "ubuntu",'
                  '"command": "env", "memory": "512"}')
        self.assertRaises(AppError, self.app.post, '/v1/containers/',
                          params=params, content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.list')
    def test_get_all_containers(self, mock_container_list,
                                mock_container_show):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers
        mock_container_show.return_value = containers[0]

        response = self.app.get('/v1/containers/')

        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters=None)
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.list')
    def test_get_all_has_status_reason_and_image_pull_policy(
            self, mock_container_list, mock_container_show):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers
        mock_container_show.return_value = containers[0]

        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))
        self.assertIn('status_reason', actual_containers[0].keys())
        self.assertIn('image_pull_policy', actual_containers[0].keys())

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_pagination_marker(self,
                                                       mock_container_list,
                                                       mock_container_show):
        container_list = []
        for id_ in range(4):
            test_container = utils.create_test_container(
                id=id_, uuid=uuidutils.generate_uuid(),
                name='container' + str(id_), context=self.context)
            container_list.append(objects.Container(self.context,
                                                    **test_container))
        mock_container_list.return_value = container_list[-1:]
        mock_container_show.return_value = container_list[-1]
        response = self.app.get('/v1/containers/?limit=3&marker=%s'
                                % container_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(container_list[-1].uuid,
                         actual_containers[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_exception(self, mock_container_list,
                                               mock_container_show):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers
        mock_container_show.side_effect = Exception

        response = self.app.get('/v1/containers/')

        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters=None)
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))

        self.assertEqual(fields.ContainerStatus.UNKNOWN,
                         actual_containers[0].get('status'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid(self, mock_container_get_by_uuid,
                             mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        response = self.app.get('/v1/containers/%s/' % test_container['uuid'])

        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_container['uuid'],
                         response.json['uuid'])

    @patch('zun.compute.rpcapi.API.container_update')
    @patch('zun.objects.Container.get_by_uuid')
    def test_patch_by_uuid(self, mock_container_get_by_uuid, mock_update):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_update.return_value = test_container_obj

        params = {'cpu': 1}
        container_uuid = test_container.get('uuid')
        response = self.app.patch_json(
            '/v1/containers/%s/' % container_uuid,
            params=params)

        self.assertEqual(200, response.status_int)
        self.assertTrue(mock_update.called)

    def _action_test(self, container, action, ident_field,
                     mock_container_action, status_code, query_param=''):
        test_container_obj = objects.Container(self.context, **container)
        ident = container.get(ident_field)
        get_by_ident_loc = 'zun.objects.Container.get_by_%s' % ident_field
        with patch(get_by_ident_loc) as mock_get_by_indent:
            mock_get_by_indent.return_value = test_container_obj
            response = self.app.post('/v1/containers/%s/%s/?%s' %
                                     (ident, action, query_param))
            self.assertEqual(status_code, response.status_int)

            # Only PUT should work, others like GET should fail
            self.assertRaises(AppError, self.app.get,
                              ('/v1/containers/%s/%s/' %
                               (ident, action)))
        if query_param:
            value = query_param.split('=')[1]
            mock_container_action.assert_called_once_with(
                mock.ANY, test_container_obj, value)
        else:
            mock_container_action.assert_called_once_with(
                mock.ANY, test_container_obj)

    @patch('zun.objects.Container.get_by_uuid')
    def test_rename_by_uuid(self, mock_container_get_by_uuid):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        with patch.object(test_container_obj, 'save') as mock_save:
            params = {'name': 'new_name'}
            container_uuid = test_container.get('uuid')
            response = self.app.post('/v1/containers/%s/rename' %
                                     container_uuid, params=params)

            mock_save.assert_called_once()
            self.assertEqual(200, response.status_int)
            self.assertEqual('new_name', test_container_obj.name)

    @patch('zun.objects.Container.get_by_uuid')
    def test_rename_with_old_name_by_uuid(self, mock_container_get_by_uuid):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        container_name = test_container.get('name')

        params = {'name': container_name}
        self.assertRaises(AppError, self.app.post,
                          '/v1/containers/%s/rename' %
                          container_uuid, params=params)

    @patch('zun.objects.Container.get_by_name')
    def test_rename_with_invalid_name_by_uuid(self,
                                              mock_container_get_by_uuid):
        invalid_names = ['a@', 'a', "", '*' * 265, " ", "     ", "a b", 'ab@']
        for value in invalid_names:
            test_container = utils.get_test_container()
            test_container_obj = \
                objects.Container(self.context, **test_container)
            mock_container_get_by_uuid.return_value = test_container_obj
            container_uuid = test_container.get('uuid')

            params = {'name': value}
            with self.assertRaisesRegexp(AppError,
                                         "Invalid input for query parameters"):
                self.app.post('/v1/containers/%s/rename' %
                              container_uuid, params=params)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_start')
    def test_start_by_uuid(self, mock_container_start, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_start.return_value = test_container_obj
        test_container = utils.get_test_container()
        self._action_test(test_container, 'start', 'uuid',
                          mock_container_start, 202)

    def test_start_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegexp(
                AppError, "Cannot start container %s in Running state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'start'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stop')
    def test_stop_by_uuid(self, mock_container_stop, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_stop.return_value = test_container_obj
        test_container = utils.get_test_container()
        self._action_test(test_container, 'stop', 'uuid',
                          mock_container_stop, 202,
                          query_param='timeout=10')

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stop')
    def test_stop_by_name_invalid_timeout_value(self,
                                                mock_container_stop,
                                                mock_validate):
        test_container = utils.get_test_container()
        with self.assertRaisesRegexp(AppError,
                                     "Invalid input for query parameters"):
            self._action_test(test_container, 'stop', 'name',
                              mock_container_stop, 202,
                              query_param='timeout=xyz')

    def test_stop_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        with self.assertRaisesRegexp(
                AppError, "Cannot stop container %s in Stopped state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'stop'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_pause')
    def test_pause_by_uuid(self, mock_container_pause, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_pause.return_value = test_container_obj
        test_container = utils.get_test_container()
        self._action_test(test_container, 'pause', 'uuid',
                          mock_container_pause, 202)

    def test_pause_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        with self.assertRaisesRegexp(
                AppError, "Cannot pause container %s in Stopped state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'pause'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_unpause')
    def test_unpause_by_uuid(self, mock_container_unpause, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_unpause.return_value = test_container_obj
        test_container = utils.get_test_container()
        self._action_test(test_container, 'unpause', 'uuid',
                          mock_container_unpause, 202)

    def test_unpause_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegexp(
                AppError,
                "Cannot unpause container %s in Running state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'unpause'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_reboot')
    def test_reboot_by_uuid(self, mock_container_reboot, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_reboot.return_value = test_container_obj
        test_container = utils.get_test_container()
        self._action_test(test_container, 'reboot', 'uuid',
                          mock_container_reboot, 202,
                          query_param='timeout=10')

    def test_reboot_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Paused')
        with self.assertRaisesRegexp(
                AppError, "Cannot reboot container %s in Paused state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'reboot'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_reboot')
    def test_reboot_by_name_wrong_timeout_value(self, mock_container_reboot,
                                                mock_validate):
        test_container = utils.get_test_container()
        with self.assertRaisesRegexp(AppError,
                                     "Invalid input for query parameters"):
            self._action_test(test_container, 'reboot', 'name',
                              mock_container_reboot, 202,
                              query_param='timeout=xyz')

    @patch('zun.compute.api.API.container_logs')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_logs_by_uuid(self, mock_get_by_uuid, mock_container_logs):
        mock_container_logs.return_value = "test"
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.app.get('/v1/containers/%s/logs/' % container_uuid)

        self.assertEqual(200, response.status_int)
        mock_container_logs.assert_called_once_with(
            mock.ANY, test_container_obj, True, True, False, 'all', None)

    @patch('zun.compute.api.API.container_logs')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_logs_with_options_by_uuid(self, mock_get_by_uuid,
                                           mock_container_logs):
        mock_container_logs.return_value = "test"
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.app.get(
            '/v1/containers/%s/logs?stderr=True&stdout=True'
            '&timestamps=False&tail=1&since=100000000' % container_uuid)
        self.assertEqual(200, response.status_int)
        mock_container_logs.assert_called_once_with(
            mock.ANY, test_container_obj, True, True, False, '1', '100000000')

    @patch('zun.compute.api.API.container_logs')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_logs_put_fails(self, mock_get_by_uuid, mock_container_logs):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        self.assertRaises(AppError, self.app.post,
                          '/v1/containers/%s/logs/' % container_uuid)
        self.assertFalse(mock_container_logs.called)

    @patch('zun.compute.api.API.container_logs')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_logs_with_invalid_since(self, mock_get_by_uuid,
                                         mock_container_logs):
        invalid_sinces = ['x11', '11x', '2000-01-01 01:01:01']
        for value in invalid_sinces:
            test_container = utils.get_test_container()
            test_container_obj = objects.Container(self.context,
                                                   **test_container)
            mock_get_by_uuid.return_value = test_container_obj

            container_uuid = test_container.get('uuid')
            params = {'since': value}

            self.assertRaises(AppError, self.app.post,
                              '/v1/containers/%s/logs' %
                              container_uuid, params)
            self.assertFalse(mock_container_logs.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_exec')
    @patch('zun.objects.Container.get_by_uuid')
    def test_execute_command_by_uuid(self, mock_get_by_uuid,
                                     mock_container_exec, mock_validate):
        mock_container_exec.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s/' % (container_uuid, 'execute')
        cmd = {'command': 'ls'}
        response = self.app.post(url, cmd)
        self.assertEqual(200, response.status_int)
        mock_container_exec.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['command'], True, False)

    def test_exec_command_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        cmd = {'command': 'ls'}
        with self.assertRaisesRegexp(
                AppError,
                "Cannot execute container %s in Stopped state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'execute'), cmd)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Container.get_by_uuid')
    def test_delete_container_by_uuid(self, mock_get_by_uuid,
                                      mock_container_delete, mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        with patch.object(test_container_obj, 'destroy') as mock_destroy:
            container_uuid = test_container.get('uuid')
            response = self.app.delete('/v1/containers/%s/' % container_uuid)

            self.assertEqual(204, response.status_int)
            mock_container_delete.assert_called_once_with(
                mock.ANY, test_container_obj, False)
            mock_destroy.assert_called_once_with(mock.ANY)

    def test_delete_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegexp(
                AppError,
                "Cannot delete container %s in Running state" % uuid):
            self.app.delete('/v1/containers/%s' % (test_object.uuid))

    def test_delete_force_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Paused')
        with self.assertRaisesRegexp(
                AppError,
                "Cannot delete_force container %s in Paused state" % uuid):
            self.app.delete('/v1/containers/%s?force=True' % test_object.uuid)

    @patch('zun.compute.api.API.container_delete')
    def test_delete_by_uuid_invalid_state_force_true(self, mock_delete):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        response = self.app.delete('/v1/containers/%s?force=True' % (
            test_object.uuid))
        self.assertEqual(204, response.status_int)

    @patch('zun.compute.api.API.container_delete')
    def test_delete_by_uuid_with_force_wrong(self, mock_delete):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid)
        mock_delete.side_effect = exception.InvalidValue
        self.assertRaises(AppError, self.app.delete,
                          '/v1/containers/%s?force=wrong' % test_object.uuid)
        self.assertTrue(mock_delete.not_called)

    def test_delete_container_with_uuid_not_found(self):
        uuid = uuidutils.generate_uuid()
        self.assertRaises(AppError, self.app.delete,
                          '/v1/containers/%s' % uuid)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_kill')
    @patch('zun.objects.Container.get_by_uuid')
    def test_kill_container_by_uuid(self,
                                    mock_get_by_uuid, mock_container_kill,
                                    mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_kill.return_value = test_container_obj
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s/' % (container_uuid, 'kill')
        cmd = {'signal': '9'}
        response = self.app.post(url, cmd)
        self.assertEqual(202, response.status_int)
        mock_container_kill.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['signal'])

    def test_kill_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        body = {'signal': 9}
        with self.assertRaisesRegexp(
                AppError, "Cannot kill container %s in Stopped state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'kill'), body)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_kill')
    @patch('zun.objects.Container.get_by_uuid')
    def test_kill_container_which_not_exist(self,
                                            mock_get_by_uuid,
                                            mock_container_kill,
                                            mock_validate):
        mock_container_kill.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_kill.side_effect = Exception

        container_uuid = "edfe2a25-2901-438d-8157-fffffd68d051"
        self.assertRaises(AppError, self.app.post,
                          '/v1/containers/%s/%s/' % (container_uuid, 'kill'))
        self.assertTrue(mock_container_kill.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_kill')
    @patch('zun.objects.Container.get_by_uuid')
    def test_kill_container_with_exception(self,
                                           mock_get_by_uuid,
                                           mock_container_kill,
                                           mock_validate):
        mock_container_kill.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_kill.side_effect = Exception

        container_uuid = test_container.get('uuid')
        self.assertRaises(AppError, self.app.post,
                          '/v1/containers/%s/%s/' % (container_uuid, 'kill'))
        self.assertTrue(mock_container_kill.called)

    @patch('zun.compute.api.API.container_kill')
    @patch('zun.objects.Container.get_by_uuid')
    def test_kill_container_with_invalid_singal(self,
                                                mock_get_by_uuid,
                                                mock_container_kill):
        invalid_signal = ['11x', 'x11']
        for value in invalid_signal:
            test_container = utils.get_test_container()
            test_container_obj = objects.Container(self.context,
                                                   **test_container)
            mock_get_by_uuid.return_value = test_container_obj

            container_uuid = test_container.get('uuid')
            params = {'signal': value}
            with self.assertRaisesRegexp(
                    AppError, "Bad response: 400 Bad Request"):
                self.app.post('/v1/containers/%s/kill/' %
                              container_uuid, params)
            self.assertFalse(mock_container_kill.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_resp_has_image_driver(self, mock_search,
                                                    mock_container_create):
        mock_container_create.side_effect = lambda x, y: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"image_driver": "glance"}')
        response = self.app.post('/v1/containers/',
                                 params=params,
                                 content_type='application/json')
        self.assertEqual(202, response.status_int)
        self.assertIn('image_driver', response.json.keys())
        self.assertEqual('glance', response.json.get('image_driver'))

    @patch('zun.compute.api.API.container_attach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_attach_container_by_uuid(self, mock_get_by_uuid,
                                      mock_container_attach):
        mock_container_attach.return_value = "ws://test"
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.app.get('/v1/containers/%s/attach/' % container_uuid)

        self.assertEqual(200, response.status_int)
        mock_container_attach.assert_called_once_with(
            mock.ANY, test_container_obj)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_attach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_attach_container_with_exception(self,
                                             mock_get_by_uuid,
                                             mock_container_attach,
                                             mock_validate):
        mock_container_attach.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_attach.side_effect = Exception

        container_uuid = test_container.get('uuid')
        self.assertRaises(AppError, self.app.get,
                          '/v1/containers/%s/attach/' % container_uuid)
        self.assertTrue(mock_container_attach.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_resize')
    @patch('zun.objects.Container.get_by_name')
    def test_resize_container_by_uuid(self,
                                      mock_get_by_uuid,
                                      mock_container_resize,
                                      mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_container_resize.return_value = test_container_obj
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_name = test_container.get('name')
        url = '/v1/containers/%s/%s/' % (container_name, 'resize')
        cmd = {'h': '100', 'w': '100'}
        response = self.app.post(url, cmd)
        self.assertEqual(200, response.status_int)
        mock_container_resize.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['h'], cmd['w'])

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_resize')
    @patch('zun.objects.Container.get_by_uuid')
    def test_resize_container_with_exception(self,
                                             mock_get_by_uuid,
                                             mock_container_resize,
                                             mock_validate):
        mock_container_resize.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_resize.side_effect = Exception

        container_uuid = test_container.get('uuid')
        body = {'h': '100', 'w': '100'}
        self.assertRaises(AppError, self.app.post,
                          '/v1/containers/%s/%s/' %
                          (container_uuid, 'resize'), body)
        self.assertTrue(mock_container_resize.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_top')
    @patch('zun.objects.Container.get_by_uuid')
    def test_top_command_by_uuid(self, mock_get_by_uuid,
                                 mock_container_top, mock_validate):
        mock_container_top.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.app.get('/v1/containers/%s/top?ps_args=aux' %
                                container_uuid)
        self.assertEqual(200, response.status_int)
        self.assertTrue(mock_container_top.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_top')
    @patch('zun.objects.Container.get_by_uuid')
    def test_top_command_invalid_ps(self, mock_get_by_uuid,
                                    mock_container_top, mock_validate):
        mock_container_top.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_top.side_effect = Exception

        container_uuid = test_container.get('uuid')
        self.assertRaises(AppError, self.app.get,
                          '/v1/containers/%s/top?ps_args=kkkk' %
                          container_uuid)
        self.assertTrue(mock_container_top.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_get_archive')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_archive_by_uuid(self,
                                 mock_get_by_uuid,
                                 container_get_archive,
                                 mock_validate):
        container_get_archive.return_value = ("", "")
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s/' % (container_uuid, 'get_archive')
        cmd = {'path': '/home/1.txt'}
        response = self.app.get(url, cmd)
        self.assertEqual(200, response.status_int)
        container_get_archive.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['path'])

    def test_get_archive_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Error')
        with self.assertRaisesRegexp(
                AppError,
                "Cannot get_archive container %s in Error state" % uuid):
            self.app.get('/v1/containers/%s/%s/' % (test_object.uuid,
                                                    'get_archive'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_put_archive')
    @patch('zun.objects.Container.get_by_uuid')
    def test_put_archive_by_uuid(self,
                                 mock_get_by_uuid,
                                 container_put_archive,
                                 mock_validate):
        container_put_archive.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s/' % (container_uuid, 'put_archive')
        cmd = {'path': '/home/',
               'data': '/home/1.tar'}
        response = self.app.post(url, cmd)
        self.assertEqual(200, response.status_int)
        container_put_archive.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['path'], cmd['data'])

    def test_put_archive_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Error')
        with self.assertRaisesRegexp(
                AppError,
                "Cannot put_archive container %s in Error state" % uuid):
            self.app.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                     'put_archive'))


class TestContainerEnforcement(api_base.FunctionalTest):

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
            'container:get_all', self.get_json, '/containers/',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:get', self.get_json,
            '/containers/%s/' % container.uuid,
            expect_errors=True)

    def test_policy_disallow_update(self):
        container = obj_utils.create_test_container(self.context)
        params = {'cpu': 1}
        self._common_policy_check(
            'container:update', self.app.patch_json,
            '/v1/containers/%s/' % container.uuid, params,
            expect_errors=True)

    def test_policy_disallow_create(self):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512"}')

        self._common_policy_check(
            'container:create', self.app.post, '/v1/containers/',
            params=params,
            content_type='application/json',
            expect_errors=True)

    def test_policy_disallow_delete(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:delete', self.app.delete,
            '/v1/containers/%s/' % container.uuid,
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
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        self._owner_check("container:get", self.get_json,
                          '/containers/%s/' % container.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        self._owner_check(
            "container:update", self.patch_json,
            '/containers/%s/' % container.uuid,
            {'cpu': 1},
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        self._owner_check(
            "container:delete", self.delete,
            '/containers/%s/' % container.uuid,
            expect_errors=True)

    def test_policy_only_owner_logs(self):
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        self._owner_check("container:logs", self.get_json,
                          '/containers/%s/logs/' % container.uuid,
                          expect_errors=True)

    def test_policy_only_owner_execute(self):
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        self._owner_check("container:execute", self.post_json,
                          '/containers/%s/execute/' % container.uuid,
                          params={'command': 'ls'}, expect_errors=True)

    def test_policy_only_owner_actions(self):
        actions = ['start', 'stop', 'reboot', 'pause', 'unpause']
        container = obj_utils.create_test_container(self.context,
                                                    user_id='another')
        for action in actions:
            self._owner_check('container:%s' % action, self.post_json,
                              '/containers/%s/%s/' % (container.uuid, action),
                              {}, expect_errors=True)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_exec_resize')
    @patch('zun.api.utils.get_resource')
    def test_execute_resize_container_exec(
            self, mock_get_resource, mock_exec_resize, mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        container_name = test_container.get('name')
        url = '/v1/containers/%s/%s/' % (container_name, 'execute_resize')
        fake_exec_id = ('7df36611fa1fc855618c2c643835d41d'
                        'ac3fe568e7688f0bae66f7bcb3cccc6c')
        kwargs = {'exec_id': fake_exec_id, 'h': '100', 'w': '100'}
        response = self.app.post(url, kwargs)
        self.assertEqual(200, response.status_int)
        mock_exec_resize.assert_called_once_with(
            mock.ANY, test_container_obj, fake_exec_id, kwargs['h'],
            kwargs['w'])
