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

from neutronclient.common import exceptions as n_exc
from oslo_utils import uuidutils

from zun.common import exception
from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils
from zun.tests.unit.objects import utils as obj_utils


class TestContainerController(api_base.FunctionalTest):
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_run_container(self, mock_search, mock_container_create,
                           mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')

        response = self.post('/v1/containers?run=true',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_container_create.call_args[1]['run'] is True)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_run_container_wrong_run_value(self, mock_search,
                                           mock_container_create):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for query parameters"):
            self.post('/v1/containers?run=xyz', params=params,
                      content_type='application/json')

    @patch('zun.compute.api.API.container_create')
    def test_run_container_wrong_memory_value(self, mock_container_create):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "3",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for field .*memory"):
            self.post('/v1/containers?run=true', params=params,
                      content_type='application/json')

    @patch('zun.compute.api.API.container_create')
    def test_run_container_wrong_cpu_value(self, mock_container_create):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512", "cpu": "100",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for field .*cpu"):
            self.post('/v1/containers?run=true', params=params,
                      content_type='application/json')

    @patch('zun.compute.api.API.container_create')
    def test_run_container_wrong_disk_value(self, mock_container_create):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512", "disk": "0",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for field .*disk"):
            self.post('/v1/containers?run=true', params=params,
                      content_type='application/json')

    def test_run_container_runtime_wrong_api_version(self):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"runtime": "runc"}')
        headers = {"OpenStack-API-Version": "container 1.4"}
        with self.assertRaisesRegex(AppError,
                                    "Invalid param runtime"):
            self.post('/v1/containers?run=true',
                      params=params, content_type='application/json',
                      headers=headers)

    def test_run_container_runtime_wrong_value(self):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"runtime": 1234}')
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for field"):
            self.post('/v1/containers?run=true',
                      params=params, content_type='application/json')

    def test_run_container_with_hostname_wrong_api_version(self):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": "env", "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"hostname": "testhost"}')
        headers = {"OpenStack-API-Version": "container 1.7"}
        with self.assertRaisesRegex(AppError,
                                    "Invalid param hostname"):
            self.post('/v1/containers?run=true',
                      params=params, content_type='application/json',
                      headers=headers)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_run_container_with_false(self, mock_search,
                                      mock_container_create,
                                      mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.post('/v1/containers?run=false',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_container_create.call_args[1]['run'] is False)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_run_container_with_wrong(self, mock_search,
                                      mock_container_create):
        mock_container_create.side_effect = exception.InvalidValue
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        self.assertRaises(AppError, self.post, '/v1/containers?run=wrong',
                          params=params, content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container(self, mock_search, mock_container_create,
                              mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertNotIn('host', response.json)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_container_create.call_args[1]['run'] is False)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.common.context.RequestContext.can')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_by_admin(
            self, mock_search, mock_container_create, mock_neutron_get_network,
            mock_can):
        mock_container_create.side_effect = lambda x, y, **z: y
        mock_can.return_value = True
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertIn('host', response.json)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_container_create.call_args[1]['run'] is False)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.compute.api.API.container_create')
    def test_create_container_image_not_specified(self, mock_container_create):

        params = ('{"name": "MyDocker",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        with self.assertRaisesRegex(AppError,
                                    "is a required property"):
            self.post('/v1/containers/',
                      params=params,
                      content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_set_project_id_and_user_id(
            self, mock_search, mock_container_create,
            mock_neutron_get_network):
        def _create_side_effect(cnxt, container, **kwargs):
            self.assertEqual(self.context.project_id, container.project_id)
            self.assertEqual(self.context.user_id, container.user_id)
            return container
        mock_container_create.side_effect = _create_side_effect

        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        self.post('/v1/containers/',
                  params=params,
                  content_type='application/json')
        mock_neutron_get_network.assert_called_once()

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_resp_has_status_reason(self, mock_search,
                                                     mock_container_create,
                                                     mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        self.assertIn('status_reason', response.json.keys())
        mock_neutron_get_network.assert_called_once()

    @patch('zun.common.policy.enforce')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.volume.cinder_api.CinderAPI.search_volume')
    @patch('zun.volume.cinder_api.CinderAPI.ensure_volume_usable')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_full_params(self, mock_search,
                                               mock_ensure_volume_usable,
                                               mock_search_volume,
                                               mock_container_delete,
                                               mock_container_create,
                                               mock_neutron_get_network,
                                               mock_policy):
        mock_policy.return_value = True
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        fake_volume_id = 'fakevolid'
        fake_volume = mock.Mock(id=fake_volume_id)
        mock_search_volume.return_value = fake_volume
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"runtime": "runc", "hostname": "testhost",'
                  '"disk": 20, "restart_policy": {"Name": "no"},'
                  '"nets": [{"network": "testpublicnet"}],'
                  '"mounts": [{"source": "s", "destination": "d"}]}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('512', c.get('memory'))
        self.assertEqual({"key1": "val1", "key2": "val2"},
                         c.get('environment'))
        self.assertEqual('runc', c.get('runtime'))
        self.assertEqual('testhost', c.get('hostname'))
        self.assertEqual(20, c.get('disk'))
        self.assertEqual({"Name": "no", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))
        self.assertNotIn('host', c)
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])
        requested_volumes = \
            mock_container_create.call_args[1]['requested_volumes']
        self.assertEqual(1, len(requested_volumes))
        self.assertEqual(fake_volume_id, requested_volumes[0].volume_id)

        # Delete the container we created
        def side_effect(*args, **kwargs):
            (ctx, cnt, force) = args
            cnt.destroy(ctx)

        mock_container_delete.side_effect = side_effect
        response = self.delete(
            '/v1/containers/%s?force=True' % c.get('uuid'))
        self.assertEqual(204, response.status_int)

        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        c = response.json['containers']
        self.assertEqual(0, len(c))
        self.assertTrue(mock_container_create.called)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_minimum_params(self,
                                                  mock_search,
                                                  mock_container_create,
                                                  mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"image": "ubuntu"}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertIsNotNone(c.get('name'))
        self.assertIsNone(None, c.get('command'))
        self.assertEqual('2048', c.get('memory'))
        self.assertEqual(1.0, c.get('cpu'))
        # TODO(kiennt): Uncomment it when bug [1] be resolved.
        #               At this time, limit disk size feature will be ready.
        # [1] https://bugs.launchpad.net/zun/+bug/1746401
        # self.assertEqual(10, c.get('disk'))
        self.assertEqual({}, c.get('environment'))
        self.assertIsNone(c.get('runtime'))
        self.assertIsNone(c.get('hostname'))
        self.assertEqual({}, c.get('restart_policy'))
        self.assertNotIn('host', c)
        mock_neutron_get_network.assert_called_once()
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_availability_zone(
            self, mock_search, mock_container_create,
            mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"],'
                  '"availability_zone": "test-az"}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('2048', c.get('memory'))
        self.assertEqual(1.0, c.get('cpu'))
        # TODO(kiennt): Uncomment it when bug [1] be resolved.
        #               At this time, limit disk size feature will be ready.
        # [1] https://bugs.launchpad.net/zun/+bug/1746401
        # self.assertEqual(10, c.get('disk'))
        self.assertEqual({}, c.get('environment'))
        self.assertNotIn('host', c)
        mock_neutron_get_network.assert_called_once()
        extra_spec = \
            mock_container_create.call_args[1]['extra_spec']
        self.assertEqual('test-az', extra_spec['availability_zone'])

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_no_retry_0(
            self,
            mock_search,
            mock_container_create,
            mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"restart_policy": {"Name": "no",'
                  '"MaximumRetryCount": "0"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('512', c.get('memory'))
        self.assertEqual({"Name": "no", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))
        self.assertNotIn('host', c)
        mock_neutron_get_network.assert_called_once()
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_no_retry_6(
            self,
            mock_search,
            mock_container_create,
            mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"restart_policy": {"Name": "no",'
                  '"MaximumRetryCount": "6"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('512', c.get('memory'))
        self.assertEqual({"Name": "no", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))
        self.assertNotIn('host', c)
        mock_neutron_get_network.assert_called_once()
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_unless_stopped(
            self,
            mock_search,
            mock_container_create,
            mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"restart_policy": {"Name": "unless-stopped",'
                  '"MaximumRetryCount": "0"}}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('512', c.get('memory'))
        self.assertEqual({"Name": "unless-stopped", "MaximumRetryCount": "0"},
                         c.get('restart_policy'))
        self.assertNotIn('host', c)
        mock_neutron_get_network.assert_called_once()
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])

    @patch('zun.common.policy.enforce')
    @patch('neutronclient.v2_0.client.Client.show_port')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_port')
    @patch('zun.network.neutron.NeutronAPI.ensure_neutron_port_usable')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_requested_neutron_port(
            self, mock_search, mock_container_delete, mock_container_create,
            mock_ensure_port_usable, mock_get_port,
            mock_get_network, mock_show_port, mock_policy):
        mock_policy.return_value = True
        mock_container_create.side_effect = lambda x, y, **z: y
        fake_port = {'network_id': 'foo', 'id': 'bar'}
        fake_private_network = {'router:external': False, 'shared': False}
        mock_get_port.return_value = fake_port
        mock_get_network.return_value = fake_private_network
        mock_show_port.return_value = {'port': fake_port}
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"nets": [{"port": "testport"}]}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('512', c.get('memory'))
        self.assertEqual({"key1": "val1", "key2": "val2"},
                         c.get('environment'))
        self.assertNotIn('host', c)
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_port['network_id'],
                         requested_networks[0]['network'])
        self.assertEqual(fake_port['id'], requested_networks[0]['port'])
        self.assertTrue(requested_networks[0]['preserve_on_delete'])

        def side_effect(*args, **kwargs):
            (ctx, cnt, force) = args
            cnt.destroy(ctx)

        # Delete the container we created
        mock_container_delete.side_effect = side_effect
        response = self.delete(
            '/v1/containers/%s?force=True' % c.get('uuid'))
        self.assertEqual(204, response.status_int)

        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        c = response.json['containers']
        self.assertEqual(0, len(c))
        self.assertTrue(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.common.context.RequestContext.can')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.network.neutron.NeutronAPI.ensure_neutron_port_usable')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_public_network(
            self, mock_search, mock_ensure_port_usable, mock_get_network,
            mock_authorize, mock_container_create):
        fake_public_network = {'id': 'fakepubnetid',
                               'router:external': True,
                               'shared': False}
        mock_get_network.return_value = fake_public_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"nets": [{"network": "testpublicnet"}]}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        fake_admin_authorize = True
        mock_authorize.return_value = fake_admin_authorize
        self.assertEqual(202, response.status_int)

        fake_not_admin_authorize = False
        mock_authorize.return_value = fake_not_admin_authorize
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json',
                             expect_errors=True)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(
            "It is not allowed to create an interface on external network %s" %
            fake_public_network['id'], response.json['errors'][0]['detail'])
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.common.context.RequestContext.can')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.network.neutron.NeutronAPI.ensure_neutron_port_usable')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_ip_addr(
            self, mock_search, mock_ensure_port_usable, mock_get_network,
            mock_authorize, mock_container_create):
        fake_network = {'id': 'fakenetid'}
        mock_get_network.return_value = fake_network
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"nets": [{"network": "fakenetid", "v4-fixed-ip": '
                  '"10.0.0.10"}]}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        fake_admin_authorize = True
        mock_authorize.return_value = fake_admin_authorize
        self.assertEqual(202, response.status_int)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.common.context.RequestContext.can')
    @patch('zun.volume.cinder_api.CinderAPI.create_volume')
    @patch('zun.volume.cinder_api.CinderAPI.ensure_volume_usable')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_create_new_volume(
            self, mock_search, mock_ensure_volume_usable, mock_create_volume,
            mock_authorize, mock_container_create, mock_container_show,
            mock_neutron_get_network):
        fake_network = {'id': 'foo'}
        mock_neutron_get_network.return_value = fake_network
        fake_volume_id = 'fakevolid'
        fake_volume = mock.Mock(id=fake_volume_id)
        mock_create_volume.return_value = fake_volume
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"mounts": [{"destination": "d", '
                  '"size": "5"}]}')
        response = self.post('/v1/containers/',
                             params=params,
                             content_type='application/json')
        self.assertEqual(202, response.status_int)
        # get all containers
        container = objects.Container.list(self.context)[0]
        container.status = 'Creating'
        mock_container_show.return_value = container
        response = self.app.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        self.assertEqual(2, len(response.json))
        c = response.json['containers'][0]
        self.assertIsNotNone(c.get('uuid'))
        self.assertEqual('MyDocker', c.get('name'))
        self.assertEqual(["env"], c.get('command'))
        self.assertEqual('Creating', c.get('status'))
        self.assertEqual('512', c.get('memory'))
        self.assertIn('host', c)
        requested_networks = \
            mock_container_create.call_args[1]['requested_networks']
        self.assertEqual(1, len(requested_networks))
        self.assertEqual(fake_network['id'], requested_networks[0]['network'])
        mock_create_volume.assert_called_once()
        requested_volumes = \
            mock_container_create.call_args[1]['requested_volumes']
        self.assertEqual(1, len(requested_volumes))
        self.assertEqual(fake_volume_id, requested_volumes[0].volume_id)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_show')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_with_restart_policy_always_and_retrycount(
            self,
            mock_search,
            mock_container_create,
            mock_container_show,
            mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"restart_policy": {"Name": "always",'
                  '"MaximumRetryCount": "1"}}')
        with self.assertRaisesRegex(
                AppError, "maximum retry count not valid with"):
            self.post('/v1/containers/',
                      params=params,
                      content_type='application/json')
        self.assertTrue(mock_container_create.not_called)
        mock_neutron_get_network.assert_called_once()

    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_invalid_long_name(self, mock_search,
                                                mock_container_create):
        # Long name
        params = ('{"name": "' + 'i' * 256 + '", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512"}')
        self.assertRaises(AppError, self.post, '/v1/containers/',
                          params=params, content_type='application/json')
        self.assertTrue(mock_container_create.not_called)

    @patch('zun.objects.Container.list')
    def test_get_all_containers(self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/')

        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters={})
        context = mock_container_list.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))
        self.assertNotIn('host', actual_containers[0])

    @patch('zun.common.context.RequestContext.can')
    @patch('zun.objects.Container.list')
    def test_get_all_containers_by_admin(self, mock_container_list, mock_can):
        mock_can.return_value = True
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/')

        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters={})
        context = mock_container_list.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))
        self.assertIn('host', actual_containers[0])

    @patch('zun.common.policy.enforce')
    @patch('zun.objects.Container.list')
    def test_get_all_containers_all_projects(self, mock_container_list,
                                             mock_policy):
        mock_policy.return_value = True
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/?all_projects=1')

        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters={})
        context = mock_container_list.call_args[0][0]
        self.assertIs(True, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))

    @patch('zun.objects.Container.list')
    def test_get_all_has_status_reason_and_image_pull_policy(
            self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/')
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))
        self.assertIn('status_reason', actual_containers[0].keys())
        self.assertIn('image_pull_policy', actual_containers[0].keys())

    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_pagination_marker(self,
                                                       mock_container_list):
        container_list = []
        for id_ in range(4):
            test_container = utils.create_test_container(
                id=id_, uuid=uuidutils.generate_uuid(),
                name='container' + str(id_), context=self.context)
            container_list.append(objects.Container(self.context,
                                                    **test_container))
        mock_container_list.return_value = container_list[-1:]
        response = self.get('/v1/containers/?limit=3&marker=%s'
                            % container_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(container_list[-1].uuid,
                         actual_containers[0].get('uuid'))

    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_filter(self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/?name=fake-name')

        mock_container_list.assert_called_once_with(
            mock.ANY, 1000, None, 'id', 'asc', filters={'name': 'fake-name'})
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))

    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_filter_disallow(
            self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/?host=fake-name',
                            expect_errors=True)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        rule = 'container:get_one:host'
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_unknown_parameter(
            self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers

        response = self.get('/v1/containers/?unknown=fake-name',
                            expect_errors=True)

        mock_container_list.assert_not_called()
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual("Unknown parameters: unknown",
                         response.json['errors'][0]['detail'])

    @patch('zun.objects.Container.list')
    def test_get_all_containers_with_exception(self, mock_container_list):
        test_container = utils.get_test_container()
        containers = [objects.Container(self.context, **test_container)]
        mock_container_list.return_value = containers
        response = self.get('/v1/containers/')
        mock_container_list.assert_called_once_with(mock.ANY,
                                                    1000, None, 'id', 'asc',
                                                    filters={})
        self.assertEqual(200, response.status_int)
        actual_containers = response.json['containers']
        self.assertEqual(1, len(actual_containers))
        self.assertEqual(test_container['uuid'],
                         actual_containers[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid(self, mock_container_get_by_uuid,
                             mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        response = self.get('/v1/containers/%s/' % test_container['uuid'])

        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])
        context = mock_container_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_container['uuid'],
                         response.json['uuid'])
        self.assertNotIn('host', response.json)

    @patch('zun.common.context.RequestContext.can')
    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_admin(self, mock_container_get_by_uuid,
                              mock_container_show, mock_can):
        mock_can.return_value = True
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        response = self.get('/v1/containers/%s/' % test_container['uuid'])

        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])
        context = mock_container_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_container['uuid'],
                         response.json['uuid'])
        self.assertIn('host', response.json)

    @patch('zun.common.policy.enforce')
    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid_all_projects(self, mock_container_get_by_uuid,
                                          mock_container_show, mock_policy):
        mock_policy.return_value = True
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        response = self.get('/v1/containers/%s/?all_projects=1' %
                            test_container['uuid'])

        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])
        context = mock_container_get_by_uuid.call_args[0][0]
        self.assertIs(True, context.all_projects)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_container['uuid'],
                         response.json['uuid'])

    @patch('zun.objects.ComputeNode.get_by_name')
    @patch('zun.compute.api.API.container_update')
    @patch('zun.objects.Container.get_by_uuid')
    def test_patch_by_uuid(self, mock_container_get_by_uuid, mock_update,
                           mock_computenode):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_update.return_value = test_container_obj
        test_host = utils.get_test_compute_node()
        numa = objects.numa.NUMATopology._from_dict(test_host['numa_topology'])
        test_host['numa_topology'] = numa
        test_host_obj = objects.ComputeNode(self.context, **test_host)
        mock_computenode.return_value = test_host_obj
        params = {'cpu': 1}
        container_uuid = test_container.get('uuid')
        response = self.patch_json(
            '/containers/%s/' % container_uuid,
            params=params)

        self.assertEqual(200, response.status_int)
        self.assertTrue(mock_update.called)
        self.assertNotIn('host', response.json)

    @patch('zun.common.context.RequestContext.can')
    @patch('zun.objects.ComputeNode.get_by_name')
    @patch('zun.compute.api.API.container_update')
    @patch('zun.objects.Container.get_by_uuid')
    def test_patch_by_admin(self, mock_container_get_by_uuid, mock_update,
                            mock_computenode, mock_can):
        mock_can.return_value = True
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_update.return_value = test_container_obj
        test_host = utils.get_test_compute_node()
        numa = objects.numa.NUMATopology._from_dict(test_host['numa_topology'])
        test_host['numa_topology'] = numa
        test_host_obj = objects.ComputeNode(self.context, **test_host)
        mock_computenode.return_value = test_host_obj
        params = {'cpu': 1}
        container_uuid = test_container.get('uuid')
        response = self.patch_json(
            '/containers/%s/' % container_uuid,
            params=params)

        self.assertEqual(200, response.status_int)
        self.assertTrue(mock_update.called)
        self.assertIn('host', response.json)

    def _action_test(self, test_container_obj, action, ident_field,
                     mock_container_action, status_code, query_param=''):
        ident = test_container_obj.uuid
        get_by_ident_loc = 'zun.objects.Container.get_by_%s' % ident_field
        with patch(get_by_ident_loc) as mock_get_by_indent:
            mock_get_by_indent.return_value = test_container_obj
            response = self.post('/v1/containers/%s/%s/?%s' %
                                 (ident, action, query_param))
            self.assertEqual(status_code, response.status_int)

            # Only PUT should work, others like GET should fail
            self.assertRaises(AppError, self.get,
                              ('/v1/containers/%s/%s/' %
                               (ident, action)))
        if query_param:
            value = query_param.split('=')[1]
            mock_container_action.assert_called_once_with(
                mock.ANY, test_container_obj, value)
        else:
            mock_container_action.assert_called_once_with(
                mock.ANY, test_container_obj)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_start')
    def test_start_by_uuid(self, mock_container_start, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        self._action_test(test_container_obj, 'start', 'uuid',
                          mock_container_start, 202)

    def test_start_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegex(
                AppError, "Cannot start container %s in Running state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'start'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stop')
    def test_stop_by_uuid(self, mock_container_stop, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        self._action_test(test_container_obj, 'stop', 'uuid',
                          mock_container_stop, 202,
                          query_param='timeout=10')

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stop')
    def test_stop_by_name_invalid_timeout_value(self,
                                                mock_container_stop,
                                                mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for query parameters"):
            self._action_test(test_container_obj, 'stop', 'name',
                              mock_container_stop, 202,
                              query_param='timeout=xyz')

    def test_stop_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        with self.assertRaisesRegex(
                AppError, "Cannot stop container %s in Stopped state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'stop'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_pause')
    def test_pause_by_uuid(self, mock_container_pause, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        self._action_test(test_container_obj, 'pause', 'uuid',
                          mock_container_pause, 202)

    def test_pause_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        with self.assertRaisesRegex(
                AppError, "Cannot pause container %s in Stopped state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'pause'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_unpause')
    def test_unpause_by_uuid(self, mock_container_unpause, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        self._action_test(test_container_obj, 'unpause', 'uuid',
                          mock_container_unpause, 202)

    def test_unpause_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegex(
                AppError,
                "Cannot unpause container %s in Running state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'unpause'))

    @patch('zun.compute.api.API.container_rebuild')
    @patch('zun.common.policy.enforce')
    def test_rebuild_container(self, mock_policy, mock_rebuild):
        mock_policy.return_value = True
        uuid = uuidutils.generate_uuid()
        utils.create_test_container(context=self.context,
                                    uuid=uuid, name="container")
        url = '/v1/containers/%s/rebuild' % uuid
        response = self.post(url)
        self.assertEqual(202, response.status_int)
        mock_rebuild.assert_called_once()

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_reboot')
    def test_reboot_by_uuid(self, mock_container_reboot, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        with patch.object(test_container_obj, 'save') as mock_save:
            self._action_test(test_container_obj, 'reboot', 'uuid',
                              mock_container_reboot, 202,
                              query_param='timeout=10')
            mock_save.assert_called_once()

    def test_reboot_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Paused')
        with self.assertRaisesRegex(
                AppError, "Cannot reboot container %s in Paused state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'reboot'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_reboot')
    def test_reboot_by_name_wrong_timeout_value(self, mock_container_reboot,
                                                mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for query parameters"):
            self._action_test(test_container_obj, 'reboot', 'name',
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
        response = self.get('/v1/containers/%s/logs/' % container_uuid)

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
        response = self.get(
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
        self.assertRaises(AppError, self.post,
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

            self.assertRaises(AppError, self.post,
                              '/v1/containers/%s/logs' %
                              container_uuid, params)
            self.assertFalse(mock_container_logs.called)

    def test_get_logs_with_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Creating')
        with self.assertRaisesRegex(
                AppError,
                "Cannot logs container %s in Creating state" % uuid):
            self.get('/v1/containers/%s/logs/' % test_object.uuid)

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
        response = self.post(url, cmd)
        self.assertEqual(200, response.status_int)
        mock_container_exec.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['command'], True, False)

    def test_exec_command_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        cmd = {'command': 'ls'}
        with self.assertRaisesRegex(
                AppError,
                "Cannot execute container %s in Stopped state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'execute'), cmd)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_exec')
    @patch('zun.objects.Container.get_by_uuid')
    def test_execute_without_command_by_uuid(self, mock_get_by_uuid,
                                             mock_container_exec,
                                             mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        cmd = {'command': ''}
        self.assertRaises(AppError, self.post,
                          '/v1/containers/%s/execute' %
                          container_uuid, cmd)
        self.assertFalse(mock_container_exec.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Container.get_by_uuid')
    def test_delete_container_by_uuid(self, mock_get_by_uuid,
                                      mock_container_delete, mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.delete('/v1/containers/%s/' % container_uuid)

        self.assertEqual(204, response.status_int)
        mock_container_delete.assert_called_once_with(
            mock.ANY, test_container_obj, False)
        context = mock_container_delete.call_args[0][0]
        self.assertIs(False, context.all_projects)

    @patch('zun.common.policy.enforce')
    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Container.get_by_uuid')
    def test_delete_container_by_uuid_all_projects(self, mock_get_by_uuid,
                                                   mock_container_delete,
                                                   mock_validate, mock_policy):
        mock_policy.return_value = True
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.delete('/v1/containers/%s/?all_projects=1' %
                               container_uuid)

        self.assertEqual(204, response.status_int)
        mock_container_delete.assert_called_once_with(
            mock.ANY, test_container_obj, False)
        context = mock_container_delete.call_args[0][0]
        self.assertIs(True, context.all_projects)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stop')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Container.get_by_uuid')
    def test_delete_container_by_uuid_with_stop(self, mock_get_by_uuid,
                                                mock_container_stop,
                                                mock_container_delete,
                                                mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        response = self.delete('/v1/containers/%s?stop=True' %
                               container_uuid)

        self.assertEqual(204, response.status_int)

    def test_delete_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        with self.assertRaisesRegex(
                AppError,
                "Cannot delete container %s in Running state" % uuid):
            self.delete('/v1/containers/%s' % (test_object.uuid))

    @patch('zun.common.policy.enforce')
    def test_delete_force_by_uuid_invalid_state(self, mock_policy):
        mock_policy.return_value = True
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Paused')
        with self.assertRaisesRegex(
                AppError,
                "Cannot delete_force container %s in Paused state" % uuid):
            self.delete('/v1/containers/%s?force=True' % test_object.uuid)

    @patch('zun.common.policy.enforce')
    @patch('zun.compute.api.API.container_delete')
    def test_delete_by_uuid_invalid_state_force_true(self, mock_delete,
                                                     mock_policy):
        mock_policy.return_value = True
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Running')
        response = self.delete('/v1/containers/%s?force=True' % (
            test_object.uuid))
        self.assertEqual(204, response.status_int)

    @patch('zun.compute.api.API.container_delete')
    def test_delete_by_uuid_with_force_wrong(self, mock_delete):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid)
        mock_delete.side_effect = exception.InvalidValue
        self.assertRaises(AppError, self.delete,
                          '/v1/containers/%s?force=wrong' % test_object.uuid)
        self.assertTrue(mock_delete.not_called)

    def test_delete_container_with_uuid_not_found(self):
        uuid = uuidutils.generate_uuid()
        self.assertRaises(AppError, self.delete,
                          '/v1/containers/%s' % uuid)

    @patch('zun.objects.Container.destroy')
    @patch('zun.common.utils.validate_container_state')
    @patch('zun.objects.Container.get_by_uuid')
    def test_delete_container_without_host(self, mock_get_by_uuid,
                                           mock_validate, mock_destroy):
        test_container = utils.get_test_container(host="")
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        response = self.delete('/v1/containers/%s/' % container_uuid)
        self.assertEqual(204, response.status_int)
        mock_validate.assert_called_once()
        mock_destroy.assert_called_once()

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
        response = self.post(url, cmd)
        self.assertEqual(202, response.status_int)
        mock_container_kill.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['signal'])

    def test_kill_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Stopped')
        body = {'signal': 9}
        with self.assertRaisesRegex(
                AppError, "Cannot kill container %s in Stopped state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
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
        self.assertRaises(AppError, self.post,
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
        self.assertRaises(AppError, self.post,
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
            with self.assertRaisesRegex(
                    AppError, "Bad response: 400 Bad Request"):
                self.post('/v1/containers/%s/kill/' %
                          container_uuid, params)
            self.assertFalse(mock_container_kill.called)

    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.compute.api.API.image_search')
    def test_create_container_resp_has_image_driver(self, mock_search,
                                                    mock_container_create,
                                                    mock_neutron_get_network):
        mock_container_create.side_effect = lambda x, y, **z: y
        # Create a container with a command
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512",'
                  '"environment": {"key1": "val1", "key2": "val2"},'
                  '"image_driver": "glance"}')
        response = self.post('/v1/containers/',
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
        response = self.get('/v1/containers/%s/attach/' % container_uuid)

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
        self.assertRaises(AppError, self.get,
                          '/v1/containers/%s/attach/' % container_uuid)
        self.assertTrue(mock_container_attach.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_resize')
    @patch('zun.objects.Container.get_by_name')
    def test_resize_by_uuid(self, mock_get_by_uuid, mock_container_resize,
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
        response = self.post(url, cmd)
        self.assertEqual(200, response.status_int)
        mock_container_resize.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['h'], cmd['w'])

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_resize')
    @patch('zun.objects.Container.get_by_uuid')
    def test_resize_with_exception(self, mock_get_by_uuid,
                                   mock_container_resize, mock_validate):
        mock_container_resize.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_resize.side_effect = Exception

        container_uuid = test_container.get('uuid')
        body = {'h': '100', 'w': '100'}
        self.assertRaises(AppError, self.post,
                          '/v1/containers/%s/%s/' %
                          (container_uuid, 'resize'), body)
        self.assertTrue(mock_container_resize.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.resize_container')
    @patch('zun.objects.Container.get_by_name')
    def test_resize_container(self, mock_get_by_uuid,
                              mock_resize_container, mock_validate):
        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        mock_resize_container.return_value = test_container_obj
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_name = test_container.get('name')
        url = '/v1/containers/%s/resize_container/' % container_name
        params = {'cpu': 1, 'memory': '512'}
        response = self.post(url, params)
        self.assertEqual(202, response.status_int)
        mock_resize_container.assert_called_once_with(
            mock.ANY, test_container_obj, params)

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
        response = self.get('/v1/containers/%s/top?ps_args=aux' %
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
        self.assertRaises(AppError, self.get,
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
        response = self.get(url, cmd)
        self.assertEqual(200, response.status_int)
        container_get_archive.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['path'])

    def test_get_archive_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Error')
        with self.assertRaisesRegex(
                AppError,
                "Cannot get_archive container %s in Error state" % uuid):
            self.get('/v1/containers/%s/%s/' % (test_object.uuid,
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
        response = self.post(url, cmd)
        self.assertEqual(200, response.status_int)
        container_put_archive.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['path'], cmd['data'])

    def test_put_archive_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        test_object = utils.create_test_container(context=self.context,
                                                  uuid=uuid, status='Error')
        with self.assertRaisesRegex(
                AppError,
                "Cannot put_archive container %s in Error state" % uuid):
            self.post('/v1/containers/%s/%s/' % (test_object.uuid,
                                                 'put_archive'))

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_stats')
    @patch('zun.objects.Container.get_by_uuid')
    def test_stats_container_by_uuid(self, mock_get_by_uuid,
                                     mock_container_stats, mock_validate):
        mock_container_stats.return_value = ""
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj

        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/stats'\
              % container_uuid
        response = self.get(url)
        self.assertEqual(200, response.status_int)
        self.assertTrue(mock_container_stats.called)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_commit')
    @patch('zun.objects.Container.get_by_name')
    def test_commit_by_name(self, mock_get_by_name,
                            mock_container_commit, mock_validate):

        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_name.return_value = test_container_obj
        mock_container_commit.return_value = None
        container_name = test_container.get('name')
        url = '/v1/containers/%s/%s/' % (container_name, 'commit')
        cmd = {'repository': 'repo', 'tag': 'tag'}
        response = self.post(url, cmd)
        self.assertEqual(202, response.status_int)
        mock_container_commit.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['repository'], cmd['tag'])

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_commit')
    @patch('zun.objects.Container.get_by_uuid')
    def test_commit_by_uuid(self, mock_get_by_uuid,
                            mock_container_commit, mock_validate):

        test_container_obj = objects.Container(self.context,
                                               **utils.get_test_container())
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_by_uuid.return_value = test_container_obj
        mock_container_commit.return_value = None
        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s/' % (container_uuid, 'commit')
        cmd = {'repository': 'repo', 'tag': 'tag'}
        response = self.post(url, cmd)
        self.assertEqual(202, response.status_int)
        mock_container_commit.assert_called_once_with(
            mock.ANY, test_container_obj, cmd['repository'], cmd['tag'])

    def test_commit_by_uuid_invalid_state(self):
        uuid = uuidutils.generate_uuid()
        cmd = {'repository': 'repo', 'tag': 'tag'}
        utils.create_test_container(context=self.context,
                                    uuid=uuid, status='Error')
        with self.assertRaisesRegex(
                AppError, "Cannot commit container %s in Error state" % uuid):
            self.post('/v1/containers/%s/commit/' % uuid, cmd)

    @patch('zun.common.utils.validate_container_state')
    @patch('zun.compute.api.API.container_exec_resize')
    @patch('zun.api.utils.get_resource')
    def test_execute_resize_container_exec(
            self, mock_get_resource, mock_exec_resize, mock_validate):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        mock_exec_resize.return_value = None
        container_name = test_container.get('name')
        url = '/v1/containers/%s/%s/' % (container_name, 'execute_resize')
        fake_exec_id = ('7df36611fa1fc855618c2c643835d41d'
                        'ac3fe568e7688f0bae66f7bcb3cccc6c')
        kwargs = {'exec_id': fake_exec_id, 'h': '100', 'w': '100'}
        response = self.post(url, kwargs)
        self.assertEqual(200, response.status_int)
        mock_exec_resize.assert_called_once_with(
            mock.ANY, test_container_obj, fake_exec_id, kwargs['h'],
            kwargs['w'])

    @mock.patch('zun.compute.api.API.add_security_group')
    @mock.patch('zun.network.neutron.NeutronAPI.find_resourceid_by_name_or_id')
    @mock.patch('zun.api.utils.get_resource')
    def test_add_security_group_by_uuid(self, mock_get_resource,
                                        mock_find_resourceid,
                                        mock_add_security_group):
        headers = {"OpenStack-API-Version": "container 1.14"}
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        mock_find_resourceid.return_value = 'fake_security_group_id'
        container_name = test_container.get('name')
        security_group_id_to_add = '5f7cf831-9a9c-4e2b-87b2-6081667f852b'
        url = '/v1/containers/%s/%s?name=%s' % (container_name,
                                                'add_security_group',
                                                security_group_id_to_add)
        response = self.post(url, headers=headers)
        self.assertEqual(202, response.status_int)
        self.assertEqual('application/json', response.content_type)
        mock_find_resourceid.assert_called_once_with(
            'security_group', security_group_id_to_add, mock.ANY)
        mock_add_security_group.assert_called_once_with(
            mock.ANY, test_container_obj, 'fake_security_group_id')

    @mock.patch('zun.compute.api.API.add_security_group')
    @mock.patch('zun.network.neutron.NeutronAPI.find_resourceid_by_name_or_id')
    @mock.patch('zun.api.utils.get_resource')
    def test_add_security_group_not_found(self, mock_get_resource,
                                          mock_find_resourceid,
                                          mock_add_security_group):
        headers = {"OpenStack-API-Version": "container 1.14"}
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        mock_find_resourceid.side_effect = n_exc.NotFound()
        container_name = test_container.get('name')
        security_group_to_add = '5f7cf831-9a9c-4e2b-87b2-6081667f852b'
        url = '/v1/containers/%s/%s?name=%s' % (container_name,
                                                'add_security_group',
                                                security_group_to_add)
        response = self.post(url, expect_errors=True, headers=headers)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(
            "Security group %s not found." % security_group_to_add,
            response.json['errors'][0]['detail'])

    @mock.patch('zun.compute.api.API.add_security_group')
    @mock.patch('zun.network.neutron.NeutronAPI.find_resourceid_by_name_or_id')
    @mock.patch('zun.api.utils.get_resource')
    def test_add_security_group_not_unique_match(self, mock_get_resource,
                                                 mock_find_resourceid,
                                                 mock_add_security_group):
        headers = {"OpenStack-API-Version": "container 1.14"}
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        mock_find_resourceid.side_effect = n_exc.NeutronClientNoUniqueMatch()
        container_name = test_container.get('name')
        security_group_to_add = '5f7cf831-9a9c-4e2b-87b2-6081667f852b'
        url = '/v1/containers/%s/%s?name=%s' % (container_name,
                                                'add_security_group',
                                                security_group_to_add)
        response = self.post(url, expect_errors=True, headers=headers)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(
            "Multiple security group matches found for name %s, "
            "use an ID to be more specific." % security_group_to_add,
            response.json['errors'][0]['detail'])

    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.compute.api.API.network_attach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_network_attach(self, mock_by_uuid, mock_attach, mock_get_network):
        built_requested_network = {
            'network': 'fake-net-id',
            'port': '',
            'router:external': False,
            'shared': False,
            'fixed_ip': '',
            'preserve_on_delete': False}
        query = 'network=private'
        self._test_network_attach(mock_by_uuid, mock_attach, mock_get_network,
                                  query, built_requested_network)
        mock_get_network.assert_called_once_with('private')

    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.compute.api.API.network_attach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_network_attach_with_fixed_ip(self, mock_by_uuid, mock_attach,
                                          mock_get_network):
        built_requested_network = {
            'network': 'fake-net-id',
            'port': '',
            'router:external': False,
            'shared': False,
            'fixed_ip': '10.0.0.3',
            'preserve_on_delete': False}
        query = 'network=private&fixed_ip=10.0.0.3'
        self._test_network_attach(mock_by_uuid, mock_attach, mock_get_network,
                                  query, built_requested_network)
        mock_get_network.assert_called_once_with('private')

    @patch('zun.network.neutron.NeutronAPI.get_neutron_port')
    @patch('zun.network.neutron.NeutronAPI.ensure_neutron_port_usable')
    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.compute.api.API.network_attach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_network_attach_with_port(self, mock_by_uuid, mock_attach,
                                      mock_get_network,
                                      mock_ensure, mock_get_port):
        mock_get_port.return_value = {
            'id': 'fake-port-id',
            'network_id': 'fake-net-id',
        }
        built_requested_network = {
            'network': 'fake-net-id',
            'port': 'fake-port-id',
            'router:external': False,
            'shared': False,
            'fixed_ip': '',
            'preserve_on_delete': True}
        query = 'port=fake-port'
        self._test_network_attach(mock_by_uuid, mock_attach, mock_get_network,
                                  query, built_requested_network)
        mock_get_port.assert_called_once_with('fake-port')
        mock_get_network.assert_called_once_with('fake-net-id')

    def _test_network_attach(self, mock_by_uuid, mock_attach, mock_get_network,
                             query, built_requested_network):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        fake_network = {'id': 'fake-net-id',
                        'router:external': False,
                        'shared': False}
        mock_get_network.return_value = fake_network
        url = '/v1/containers/%s/%s?%s' % (container_uuid, 'network_attach',
                                           query)
        response = self.post(url)
        self.assertEqual(200, response.status_int)
        mock_attach.assert_called_once_with(mock.ANY, test_container_obj,
                                            built_requested_network)

    @patch('zun.network.neutron.NeutronAPI.get_neutron_network')
    @patch('zun.compute.api.API.network_detach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_network_detach(self, mock_by_uuid, mock_detach, mock_get_network):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        mock_get_network.return_value = {'id': 'private'}
        mock_detach.return_value = None
        url = '/v1/containers/%s/%s?network=%s' % (container_uuid,
                                                   'network_detach',
                                                   'private')
        response = self.post(url)
        self.assertEqual(202, response.status_int)
        mock_detach.assert_called_once_with(mock.ANY, test_container_obj,
                                            'private')

    @patch('zun.network.neutron.NeutronAPI.get_neutron_port')
    @patch('zun.compute.api.API.network_detach')
    @patch('zun.objects.Container.get_by_uuid')
    def test_network_detach_with_port(self, mock_by_uuid, mock_detach,
                                      mock_get_port):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        mock_get_port.return_value = {'network_id': 'fake-net-id'}
        mock_detach.return_value = None
        url = '/v1/containers/%s/%s?port=%s' % (container_uuid,
                                                'network_detach',
                                                'fake-port')
        response = self.post(url)
        self.assertEqual(202, response.status_int)
        mock_detach.assert_called_once_with(mock.ANY, test_container_obj,
                                            'fake-net-id')

    @patch('zun.objects.Container.get_by_uuid')
    def test_network_list(self, mock_container_get_by_uuid):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        container_uuid = test_container.get('uuid')
        url = '/v1/containers/%s/%s' % (container_uuid, 'network_list')
        response = self.get(url)
        self.assertEqual(200, response.status_int)
        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])
        self._assert_networks(test_container['addresses'],
                              response.json['networks'])

    def _assert_networks(self, addresses, networks):
        self.assertEqual(len(addresses), len(networks))
        for network in networks:
            address_list = addresses[network['net_id']]
            self.assertEqual(len(address_list), len(network['fixed_ips']))
            for address in address_list:
                matched = 0
                for fixed_ip in network['fixed_ips']:
                    if (address['addr'] == fixed_ip['ip_address'] and
                            address['version'] == fixed_ip['version'] and
                            address['subnet_id'] == fixed_ip['subnet_id'] and
                            address['port'] == network['port_id']):
                        matched += 1
                self.assertEqual(1, matched)

    @mock.patch('zun.compute.api.API.remove_security_group')
    @mock.patch('zun.network.neutron.NeutronAPI.find_resourceid_by_name_or_id')
    @mock.patch('zun.api.utils.get_resource')
    def test_remove_security_group_by_uuid(self, mock_get_resource,
                                           mock_find_resourceid,
                                           mock_remove_security_group):
        headers = {"OpenStack-API-Version": "container 1.14"}
        test_container = utils.get_test_container(
            security_groups=['affb9021-964d-4b1b-80a8-9b9db60497e4'])
        test_container_obj = objects.Container(self.context, **test_container)
        mock_get_resource.return_value = test_container_obj
        mock_find_resourceid.return_value = \
            test_container_obj.security_groups[0]
        container_name = test_container.get('name')
        security_group_id_to_remove = test_container_obj.security_groups[0]
        url = '/v1/containers/%s/%s?name=%s' % (container_name,
                                                'remove_security_group',
                                                security_group_id_to_remove)
        response = self.post(url, headers=headers)
        self.assertEqual(202, response.status_int)
        self.assertEqual('application/json', response.content_type)
        mock_find_resourceid.assert_called_once_with(
            'security_group', security_group_id_to_remove, mock.ANY)
        mock_remove_security_group.assert_called_once_with(
            mock.ANY, test_container_obj,
            test_container_obj.security_groups[0])


class TestContainerEnforcement(api_base.FunctionalTest):

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
            'container:get_all', self.get, '/v1/containers/',
            expect_errors=True)

    def test_policy_disallow_get_all_all_projects(self):
        self._common_policy_check(
            'container:get_all_all_projects',
            self.get, '/v1/containers/?all_projects=1',
            expect_errors=True,
            bypass_rules={'container:get_all': 'project_id:fake_project'})

    def test_policy_disallow_get_one(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:get_one', self.get,
            '/v1/containers/%s/' % container.uuid,
            expect_errors=True)

    def test_policy_disallow_get_one_all_projects(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:get_one_all_projects', self.get,
            '/v1/containers/%s/?all_projects=1' % container.uuid,
            expect_errors=True)

    def test_policy_disallow_update(self):
        container = obj_utils.create_test_container(self.context)
        params = {'cpu': 1}
        self._common_policy_check(
            'container:update', self.patch_json,
            '/containers/%s/' % container.uuid, params,
            expect_errors=True)

    def test_policy_disallow_create(self):
        params = ('{"name": "MyDocker", "image": "ubuntu",'
                  '"command": ["env"], "memory": "512"}')

        self._common_policy_check(
            'container:create', self.post, '/v1/containers/',
            params=params,
            content_type='application/json',
            expect_errors=True)

    def test_policy_disallow_delete(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:delete', self.delete,
            '/v1/containers/%s/' % container.uuid,
            expect_errors=True)

    def test_policy_disallow_delete_all_projects(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:delete_all_projects', self.delete,
            '/v1/containers/%s/?all_projects=1' % container.uuid,
            expect_errors=True)

    def test_policy_disallow_delete_force(self):
        container = obj_utils.create_test_container(self.context)
        self._common_policy_check(
            'container:delete_force', self.delete,
            '/v1/containers/%s/?force=True' % container.uuid,
            expect_errors=True,
            bypass_rules={'container:delete': 'project_id:fake_project'})

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
        self._owner_check("container:get_one", self.get_json,
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


class TestContainerActionController(api_base.FunctionalTest):

    def _format_action(self, action, expect_traceback=True):
        '''Remove keys that aren't serialized.'''
        to_delete = ('id', 'finish_time', 'created_at', 'updated_at',
                     'deleted_at', 'deleted')
        for key in to_delete:
            if key in action:
                del (action[key])
        for event in action.get('events', []):
            self._format_event(event, expect_traceback)
        return action

    def _format_event(self, event, expect_traceback=True):
        '''Remove keys that aren't serialized.'''
        to_delete = ['id', 'created_at', 'updated_at', 'deleted_at', 'deleted',
                     'action_id']
        if not expect_traceback:
            event['traceback'] = None
        for key in to_delete:
            if key in event:
                del (event[key])
        return event

    @mock.patch('zun.objects.Container.get_by_uuid')
    @mock.patch('zun.objects.ContainerAction.get_by_container_uuid')
    def test_list_actions(self, mock_get_by_container_uuid,
                          mock_container_get_by_uuid):
        test_container = utils.get_test_container()
        test_action = utils.get_test_action_value(
            container_uuid=test_container['uuid'])

        container_object = objects.Container(self.context, **test_container)
        action_object = objects.ContainerAction(self.context, **test_action)

        mock_container_get_by_uuid.return_value = container_object
        mock_get_by_container_uuid.return_value = [action_object]
        response = self.get('/v1/containers/%s/container_actions' %
                            test_container['uuid'])

        mock_get_by_container_uuid.assert_called_once_with(
            mock.ANY,
            test_container['uuid'])

        self.assertEqual(200, response.status_int)
        self.assertEqual(
            self._format_action(test_action),
            self._format_action(response.json['containerActions'][0]))

    @mock.patch('zun.objects.Container.get_by_uuid')
    @mock.patch('zun.common.policy.enforce')
    @mock.patch('zun.objects.ContainerActionEvent.get_by_action')
    @mock.patch('zun.objects.ContainerAction.get_by_request_id')
    def test_get_action_with_events_allowed(self, mock_get_by_request_id,
                                            mock_get_by_action, mock_policy,
                                            mock_container_get_by_uuid):
        mock_policy.return_value = True
        test_container = utils.get_test_container()
        test_action = utils.get_test_action_value(
            container_uuid=test_container['uuid'])
        test_event = utils.get_test_action_event_value(
            action_id=test_action['id'])
        test_action['events'] = [test_event]

        container_object = objects.Container(self.context, **test_container)
        action_object = objects.ContainerAction(self.context, **test_action)
        event_object = objects.ContainerActionEvent(self.context, **test_event)

        mock_container_get_by_uuid.return_value = container_object
        mock_get_by_request_id.return_value = action_object
        mock_get_by_action.return_value = [event_object]

        response = self.get('/v1/containers/%s/container_actions/%s' % (
            test_container['uuid'], test_action['request_id']))

        mock_get_by_request_id.assert_called_once_with(
            mock.ANY, test_container['uuid'], test_action['request_id'])
        mock_get_by_action.assert_called_once_with(mock.ANY, test_action['id'])

        self.assertEqual(200, response.status_int)
        self.assertEqual(self._format_action(test_action),
                         self._format_action(response.json))

    @mock.patch('zun.objects.Container.get_by_uuid')
    @mock.patch('zun.common.policy.enforce')
    @mock.patch('zun.objects.ContainerActionEvent.get_by_action')
    @mock.patch('zun.objects.ContainerAction.get_by_request_id')
    def test_get_action_with_events_not_allowed(self, mock_get_by_request_id,
                                                mock_get_by_action,
                                                mock_policy,
                                                mock_container_get_by_uuid):
        mock_policy.return_value = False
        test_container = utils.get_test_container()
        container_obj = objects.Container(self.context, **test_container)
        test_action = utils.get_test_action_value(
            container_uuid=test_container['uuid'])
        test_event = utils.get_test_action_event_value(
            action_id=test_action['id'])
        test_action['events'] = [test_event]
        action_object = objects.ContainerAction(self.context, **test_action)
        event_object = objects.ContainerActionEvent(self.context, **test_event)

        mock_container_get_by_uuid.return_value = container_obj
        mock_get_by_request_id.return_value = action_object
        mock_get_by_action.return_value = [event_object]

        response = self.get('/v1/containers/%s/container_actions/%s' % (
            test_container['uuid'], test_action['request_id']))

        mock_get_by_request_id.assert_called_once_with(
            mock.ANY, test_container['uuid'], test_action['request_id'])
        mock_get_by_action.assert_called_once_with(mock.ANY, test_action['id'])

        self.assertEqual(200, response.status_int)
        self.assertEqual(self._format_action(test_action,
                                             expect_traceback=False),
                         self._format_action(response.json))

    @mock.patch('zun.objects.Container.get_by_uuid')
    @mock.patch('zun.objects.ContainerAction.get_by_request_id')
    def test_action_not_found(self, mock_get_by_request_id,
                              mock_container_get_by_uuid):

        test_container = utils.get_test_container()
        container_obj = objects.Container(self.context, **test_container)

        mock_container_get_by_uuid.return_value = container_obj
        mock_get_by_request_id.return_value = None

        fake_request_id = 'request'

        self.assertRaises(AppError, self.get,
                          ('/v1/containers/%s/container_actions/%s' %
                           (test_container['uuid'], fake_request_id)))
        mock_get_by_request_id.assert_called_once_with(
            mock.ANY, test_container['uuid'], fake_request_id)

    @mock.patch('zun.objects.Container.get_by_uuid')
    def test_container_not_found(self, mock_container_get_by_uuid):
        test_container = utils.get_test_container()

        self.assertRaises(AppError, self.get,
                          ('/v1/containers/%s/container_actions'
                           % test_container['uuid']))
        mock_container_get_by_uuid.assert_called_once_with(
            mock.ANY, test_container['uuid'])


class TestContainerActionEnforcement(api_base.FunctionalTest):

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

    def test_list_actions_disallow_by_project(self):
        container = obj_utils.create_test_container(self.context)

        self._common_policy_check(
            'container:actions', self.get,
            '/v1/containers/%s/container_actions/' % container.uuid,
            expect_errors=True)

    def test_get_action_disallow_by_project(self):
        container = obj_utils.create_test_container(self.context)

        self._common_policy_check(
            'container:actions', self.get,
            '/v1/containers/%s/container_actions/fake_request' %
            container.uuid, expect_errors=True)
