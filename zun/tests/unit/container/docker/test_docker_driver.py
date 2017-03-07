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

from docker import errors
import mock

from zun import conf
from zun.container.docker.driver import DockerDriver
from zun.container.docker.driver import NovaDockerDriver
from zun.container.docker import utils as docker_utils
from zun import objects
from zun.objects import fields
from zun.tests.unit.container import base
from zun.tests.unit.db import utils as db_utils

LSCPU_ON = """# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# Socket,CPU,Online
0,0,Y
0,8,Y"""

CONF = conf.CONF

_numa_node = {
    'id': 0,
    'cpuset': [8],
    'pinned_cpus': []
}

_numa_topo_spec = [_numa_node]


class TestDockerDriver(base.DriverTestCase):
    def setUp(self):
        super(TestDockerDriver, self).setUp()
        self.driver = DockerDriver()
        dfc_patcher = mock.patch.object(docker_utils, 'docker_client')
        docker_client = dfc_patcher.start()
        self.dfc_context_manager = docker_client.return_value
        self.mock_docker = mock.MagicMock()
        container_dict = db_utils.create_test_container(context=self.context)
        self.mock_default_container = mock.MagicMock(**container_dict)
        self.dfc_context_manager.__enter__.return_value = self.mock_docker
        self.addCleanup(dfc_patcher.stop)

    def test_inspect_image_path_is_none(self):
        self.mock_docker.inspect_image = mock.Mock()
        mock_image = mock.MagicMock()
        self.driver.inspect_image(mock_image)
        self.mock_docker.inspect_image.assert_called_once_with(mock_image)

    def test_inspect_image_path_is_not_none(self):
        self.mock_docker.load_image = mock.Mock()
        self.mock_docker.inspect_image = mock.Mock()
        mock_open_file = mock.mock_open(read_data='test_data')
        with mock.patch('zun.container.docker.driver.open', mock_open_file):
            mock_image = mock.MagicMock()
            self.driver.inspect_image(mock_image, 'test')
            self.mock_docker.load_image.assert_called_once_with('test_data')
            self.mock_docker.inspect_image.assert_called_once_with(
                mock_image)

    def test_images(self):
        self.mock_docker.images = mock.Mock()
        self.driver.images(repo='test')
        self.mock_docker.images.assert_called_once_with('test', False)

    @mock.patch('zun.objects.container.Container.save')
    def test_create_image_path_is_none(self, mock_save):
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        image = {'path': ''}
        mock_container = self.mock_default_container
        result_container = self.driver.create(self.context, mock_container,
                                              'test_sandbox', image)
        host_config = {}
        host_config['network_mode'] = 'container:test_sandbox'
        host_config['ipc_mode'] = 'container:test_sandbox'
        host_config['volumes_from'] = 'test_sandbox'
        host_config['mem_limit'] = '512m'
        host_config['cpu_quota'] = 100000
        host_config['cpu_period'] = 100000
        host_config['restart_policy'] = {'Name': 'no', 'MaximumRetryCount': 0}
        self.mock_docker.create_host_config.assert_called_once_with(
            **host_config)

        kwargs = {
            'name': 'zun-ea8e2a25-2901-438d-8157-de7ffd68d051',
            'command': 'fake_command',
            'environment': {'key1': 'val1', 'key2': 'val2'},
            'working_dir': '/home/ubuntu',
            'labels': {'key1': 'val1', 'key2': 'val2'},
            'host_config': {'Id1': 'val1', 'key2': 'val2'},
            'stdin_open': True,
            'tty': True,
        }
        self.mock_docker.create_container.assert_called_once_with(
            mock_container.image, **kwargs)
        self.assertEqual(result_container.container_id, 'val1')
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.STOPPED)

    @mock.patch('zun.objects.container.Container.save')
    def test_create_image_path_is_not_none(self, mock_save):
        self.mock_docker.load_image = mock.Mock(return_value='load_test')
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        mock_open_file = mock.mock_open(read_data='test_data')
        with mock.patch('zun.container.docker.driver.open', mock_open_file):
            mock_container = self.mock_default_container
            result_container = self.driver.create(self.context,
                                                  mock_container,
                                                  'test_sandbox',
                                                  {'path': 'test_path'})
            self.mock_docker.load_image.assert_called_once_with('test_data')

            host_config = {}
            host_config['network_mode'] = 'container:test_sandbox'
            host_config['ipc_mode'] = 'container:test_sandbox'
            host_config['volumes_from'] = 'test_sandbox'
            host_config['mem_limit'] = '512m'
            host_config['cpu_quota'] = 100000
            host_config['cpu_period'] = 100000
            host_config['restart_policy'] = {'Name': 'no',
                                             'MaximumRetryCount': 0}
            self.mock_docker.create_host_config.assert_called_once_with(
                **host_config)

            kwargs = {
                'command': 'fake_command',
                'environment': {'key1': 'val1', 'key2': 'val2'},
                'working_dir': '/home/ubuntu',
                'labels': {'key1': 'val1', 'key2': 'val2'},
                'host_config': {'Id1': 'val1', 'key2': 'val2'},
                'name': 'zun-ea8e2a25-2901-438d-8157-de7ffd68d051',
                'stdin_open': True,
                'tty': True,
            }
            self.mock_docker.create_container.assert_called_once_with(
                mock_container.image, **kwargs)
            self.assertEqual(result_container.container_id, 'val1')
            self.assertEqual(result_container.status,
                             fields.ContainerStatus.STOPPED)

    def test_delete_success(self):
        self.mock_docker.remove_container = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.delete(mock_container, True)
        self.mock_docker.remove_container.assert_called_once_with(
            mock_container.container_id, force=True)

    def test_delete_fail_no_result(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.remove_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.driver.delete(mock_container, True)
            self.mock_docker.remove_container.assert_called_once_with(
                mock_container.container_id, force=True)
            self.assertEqual(1, mock_init.call_count)

    def test_delete_fail_raise_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='test') as mock_init:
            self.mock_docker.remove_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.assertRaises(errors.APIError, self.driver.delete,
                              mock_container,
                              True)
            self.mock_docker.remove_container.assert_called_once_with(
                mock_container.container_id, force=True)
            self.assertEqual(1, mock_init.call_count)

    def test_list(self):
        self.mock_docker.list_instances = mock.Mock()
        self.driver.list()
        self.mock_docker.list_instances.assert_called_once_with()

    def test_show_success(self):
        self.mock_docker.inspect_container = mock.Mock(return_value={})
        mock_container = mock.MagicMock()
        self.driver.show(mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)

    def test_show_fail_container_id_is_none(self):
        mock_container = mock.MagicMock()
        mock_container.container_id = None
        result_container = self.driver.show(mock_container)
        self.assertIsNone(result_container.container_id)

    def test_show_fail_container_status_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            result_container = self.driver.show(mock_container)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(result_container.status,
                             fields.ContainerStatus.ERROR)
            self.assertEqual(1, mock_init.call_count)

    def test_show_fail_api_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='test') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.assertRaises(errors.APIError, self.driver.show,
                              mock_container)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(1, mock_init.call_count)

    def test_reboot(self):
        self.mock_docker.restart = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.reboot(mock_container, '30')
        self.mock_docker.restart.assert_called_once_with(
            mock_container.container_id, timeout=30)
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.RUNNING)

    def test_stop(self):
        self.mock_docker.stop = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.stop(mock_container, '30')
        self.mock_docker.stop.assert_called_once_with(
            mock_container.container_id,
            timeout=30)
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.STOPPED)

    def test_start(self):
        self.mock_docker.start = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.start(mock_container)
        self.mock_docker.start.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.RUNNING)

    def test_pause(self):
        self.mock_docker.pause = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.pause(mock_container)
        self.mock_docker.pause.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.PAUSED)

    def test_unpause(self):
        self.mock_docker.unpause = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.unpause(mock_container)
        self.mock_docker.unpause.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         fields.ContainerStatus.RUNNING)

    def test_show_logs(self):
        self.mock_docker.get_container_logs = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.show_logs(mock_container)
        self.mock_docker.get_container_logs.assert_called_once_with(
            mock_container.container_id, True, True, False, False,
            'all', None)

    def test_execute(self):
        self.mock_docker.exec_create = mock.Mock(return_value={'Id': 'test'})
        self.mock_docker.exec_start = mock.Mock(return_value='test')
        self.mock_docker.exec_inspect = mock.Mock(
            return_value={u'ExitCode': 0})
        mock_container = mock.MagicMock()
        self.driver.execute(mock_container, 'ls')
        self.mock_docker.exec_create.assert_called_once_with(
            mock_container.container_id, 'ls', True, True, False)
        self.mock_docker.exec_start.assert_called_once_with('test', False,
                                                            False, False)
        self.mock_docker.exec_inspect.assert_called_once()

    def test_kill_successful_signal_is_none(self):
        self.mock_docker.kill = mock.Mock()
        self.mock_docker.inspect_container = mock.Mock(return_value={})
        mock_container = mock.MagicMock()
        self.driver.kill(mock_container, signal=None)
        self.mock_docker.kill.assert_called_once_with(
            mock_container.container_id)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)

    def test_kill_successful_signal_is_not_none(self):
        self.mock_docker.kill = mock.Mock()
        self.mock_docker.inspect_container = mock.Mock(return_value={})
        mock_container = mock.MagicMock()
        self.driver.kill(mock_container, signal='test')
        self.mock_docker.kill.assert_called_once_with(
            mock_container.container_id,
            'test')
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)

    def test_kill_fail_container_status_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.kill = mock.Mock()
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            result_container = self.driver.kill(mock_container,
                                                signal='test')
            self.mock_docker.kill.assert_called_once_with(
                mock_container.container_id, 'test')
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(result_container.status,
                             fields.ContainerStatus.ERROR)
            self.assertEqual(1, mock_init.call_count)

    def test_kill_fail_api_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='test') as mock_init:
            self.mock_docker.kill = mock.Mock()
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.assertRaises(errors.APIError, self.driver.kill,
                              mock_container,
                              'test')
            self.mock_docker.kill.assert_called_once_with(
                mock_container.container_id, 'test')
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(1, mock_init.call_count)

    def test_resize(self):
        self.mock_docker.resize = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.resize(mock_container, "100", "100")
        self.mock_docker.resize.assert_called_once_with(
            mock_container.container_id, 100, 100)

    @mock.patch('zun.container.docker.driver.DockerDriver.get_sandbox_name')
    def test_create_sandbox(self, mock_get_sandbox_name):
        sandbox_name = 'my_test_sandbox'
        mock_get_sandbox_name.return_value = sandbox_name
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.start()
        mock_container = mock.MagicMock()
        result_sandbox_id = self.driver.create_sandbox(self.context,
                                                       mock_container,
                                                       'kubernetes/pause')
        self.mock_docker.create_container.assert_called_once_with(
            'kubernetes/pause', name=sandbox_name, hostname=sandbox_name)
        self.assertEqual(result_sandbox_id, 'val1')

    @mock.patch('zun.container.docker.driver.DockerDriver.get_sandbox_name')
    def test_create_sandbox_with_long_name(self, mock_get_sandbox_name):
        sandbox_name = 'x' * 100
        mock_get_sandbox_name.return_value = sandbox_name
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.start()
        mock_container = mock.MagicMock()
        result_sandbox_id = self.driver.create_sandbox(self.context,
                                                       mock_container,
                                                       'kubernetes/pause')
        self.mock_docker.create_container.assert_called_once_with(
            'kubernetes/pause', name=sandbox_name, hostname=sandbox_name[:63])
        self.assertEqual(result_sandbox_id, 'val1')

    def test_delete_sandbox(self):
        self.mock_docker.remove_container = mock.Mock()
        self.driver.delete_sandbox(context=self.context,
                                   sandbox_id='test_sandbox_id')
        self.mock_docker.remove_container.assert_called_once_with(
            'test_sandbox_id', force=True)

    def test_stop_sandbox(self):
        self.mock_docker.stop = mock.Mock()
        self.driver.stop_sandbox(context=self.context,
                                 sandbox_id='test_sandbox_id')
        self.mock_docker.stop.assert_called_once_with('test_sandbox_id')

    def test_get_sandbox_none_id(self):
        mock_container = mock.MagicMock()
        mock_container.meta = None
        result_sandbox_id = self.driver.get_sandbox_id(mock_container)
        self.assertIsNone(result_sandbox_id)

    def test_get_sandbox_not_none_id(self):
        mock_container = mock.MagicMock()
        result_sandbox_id = self.driver.get_sandbox_id(mock_container)
        self.assertEqual(result_sandbox_id,
                         mock_container.meta.get('sandbox_id', None))

    def test_set_sandbox_id(self):
        mock_container = mock.MagicMock(meta={'sandbox_id': 'test_sandbox_id'})
        self.driver.set_sandbox_id(mock_container, 'test_sandbox_id')
        self.assertEqual(mock_container.meta['sandbox_id'],
                         'test_sandbox_id')

    def test_get_sandbox_name(self):
        mock_container = mock.MagicMock(
            uuid='ea8e2a25-2901-438d-8157-de7ffd68d051')
        result_sanbox_name = self.driver.get_sandbox_name(mock_container)
        self.assertEqual(result_sanbox_name,
                         'zun-sandbox-ea8e2a25-2901-438d-8157-de7ffd68d051')

    def test_get_container_name(self):
        mock_container = mock.MagicMock(
            uuid='ea8e2a25-2901-438d-8157-de7ffd68d051')
        result_container_name = self.driver.get_container_name(
            mock_container)
        self.assertEqual(result_container_name,
                         'zun-ea8e2a25-2901-438d-8157-de7ffd68d051')

    @mock.patch('zun.container.docker.driver.DockerDriver.get_sandbox_id')
    def test_get_addresses(self, mock_get_sandbox_id):
        mock_get_sandbox_id.return_value = 'test_sandbox_id'
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'NetworkSettings': {'IPAddress': '127.0.0.1'}})
        mock_container = mock.MagicMock()
        result_addresses = self.driver.get_addresses(self.context,
                                                     mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            'test_sandbox_id')
        self.assertEqual(result_addresses,
                         {'default': [{'addr': '127.0.0.1', }, ], })


class TestNovaDockerDriver(base.DriverTestCase):
    def setUp(self):
        super(TestNovaDockerDriver, self).setUp()
        self.driver = NovaDockerDriver()

    @mock.patch(
        'zun.container.docker.driver.NovaDockerDriver.get_sandbox_name')
    @mock.patch('zun.common.nova.NovaClient')
    @mock.patch('zun.container.docker.driver.NovaDockerDriver._ensure_active')
    @mock.patch('zun.container.docker.driver.'
                'NovaDockerDriver._find_container_by_server_name')
    def test_create_sandbox(self, mock_find_container_by_server_name,
                            mock_ensure_active, mock_nova_client,
                            mock_get_sandbox_name):
        nova_client_instance = mock.MagicMock()
        nova_client_instance.create_server.return_value = 'server_instance'
        mock_get_sandbox_name.return_value = 'test_sanbox_name'
        mock_nova_client.return_value = nova_client_instance
        mock_ensure_active.return_value = True
        mock_find_container_by_server_name.return_value = \
            'test_container_name_id'
        db_container = db_utils.create_test_container(context=self.context,
                                                      host=conf.CONF.host)
        mock_container = mock.MagicMock(**db_container)
        result_sandbox_id = self.driver.create_sandbox(self.context,
                                                       mock_container)
        mock_get_sandbox_name.assert_called_once_with(mock_container)
        nova_client_instance.create_server.assert_called_once_with(
            name='test_sanbox_name', image='kubernetes/pause',
            flavor='m1.tiny', key_name=None,
            nics='auto', availability_zone=':{0}:'.format(conf.CONF.host))
        mock_ensure_active.assert_called_once_with(nova_client_instance,
                                                   'server_instance')
        mock_find_container_by_server_name.assert_called_once_with(
            'test_sanbox_name')
        self.assertEqual(result_sandbox_id, 'test_container_name_id')

    @mock.patch('zun.common.nova.NovaClient')
    @mock.patch('zun.container.docker.driver.'
                'NovaDockerDriver._find_server_by_container_id')
    @mock.patch('zun.container.docker.driver.NovaDockerDriver._ensure_deleted')
    def test_delete_sandbox(self, mock_ensure_delete,
                            mock_find_server_by_container_id, mock_nova_client
                            ):
        nova_client_instance = mock.MagicMock()
        nova_client_instance.delete_server.return_value = 'delete_server_id'
        mock_nova_client.return_value = nova_client_instance
        mock_find_server_by_container_id.return_value = 'test_test_server_name'
        mock_ensure_delete.return_value = True
        self.driver.delete_sandbox(self.context, sandbox_id='test_sandbox_id')
        mock_find_server_by_container_id.assert_called_once_with(
            'test_sandbox_id')
        nova_client_instance.delete_server.assert_called_once_with(
            'test_test_server_name')
        mock_ensure_delete.assert_called_once_with(nova_client_instance,
                                                   'delete_server_id')

    @mock.patch('zun.common.nova.NovaClient')
    @mock.patch('zun.container.docker.driver.'
                'NovaDockerDriver._find_server_by_container_id')
    def test_stop_sandbox(self, mock_find_server_by_container_id,
                          mock_nova_client):
        nova_client_instance = mock.MagicMock()
        nova_client_instance.stop_server.return_value = 'stop_server_id'
        mock_nova_client.return_value = nova_client_instance
        mock_find_server_by_container_id.return_value = 'test_test_server_name'
        self.driver.stop_sandbox(self.context, sandbox_id='test_sandbox_id')
        mock_find_server_by_container_id.assert_called_once_with(
            'test_sandbox_id')
        nova_client_instance.stop_server.assert_called_once_with(
            'test_test_server_name')

    @mock.patch('zun.container.docker.driver.'
                'NovaDockerDriver._find_server_by_container_id')
    @mock.patch('zun.container.docker.driver.NovaDockerDriver.get_sandbox_id')
    @mock.patch('zun.common.nova.NovaClient')
    def test_get_addresses(self, mock_nova_client, mock_get_sandbox_id,
                           mock_find_server_by_container_id):
        nova_client_instance = mock.MagicMock()
        nova_client_instance.get_addresses.return_value = 'test_address'
        mock_nova_client.return_value = nova_client_instance
        mock_get_sandbox_id.return_value = 'test_sanbox_id'
        mock_find_server_by_container_id.return_value = 'test_test_server_name'
        mock_container = mock.MagicMock()
        result_address = self.driver.get_addresses(self.context,
                                                   mock_container)
        mock_get_sandbox_id.assert_called_once_with(mock_container)
        mock_find_server_by_container_id.assert_called_once_with(
            'test_sanbox_id')
        nova_client_instance.get_addresses.assert_called_once_with(
            'test_test_server_name')
        self.assertEqual(result_address, 'test_address')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_get_available_resources(self, mock_output):
        mock_output.return_value = LSCPU_ON
        conf.CONF.set_override('floating_cpu_set', "0")
        node_obj = objects.ComputeNode()
        self.driver.get_available_resources(node_obj)
        self.assertEqual(_numa_topo_spec, node_obj.numa_topology.to_list())
