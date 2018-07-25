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

from oslo_utils import units
from oslo_utils import uuidutils

from zun.common import consts
from zun.common import exception
from zun import conf
from zun.container.docker.driver import DockerDriver
from zun.container.docker import utils as docker_utils
from zun import objects
from zun.objects.container import Container
from zun.tests.unit.container import base
from zun.tests.unit.db import utils
from zun.tests.unit.objects import utils as obj_utils

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

    @mock.patch('zun.container.docker.driver.DockerDriver.'
                '_get_host_storage_info')
    def setUp(self, mock_get):
        super(TestDockerDriver, self).setUp()
        self.driver = DockerDriver()
        dfc_patcher = mock.patch.object(docker_utils, 'docker_client')
        docker_client = dfc_patcher.start()
        self.dfc_context_manager = docker_client.return_value
        self.mock_docker = mock.MagicMock()
        self.mock_default_container = obj_utils.get_test_container(
            self.context)
        self.dfc_context_manager.__enter__.return_value = self.mock_docker
        self.addCleanup(dfc_patcher.stop)

    def test_inspect_image_path_is_none(self):
        self.mock_docker.inspect_image = mock.Mock()
        mock_image = mock.MagicMock()
        self.driver.inspect_image(mock_image)
        self.mock_docker.inspect_image.assert_called_once_with(mock_image)

    def test_get_image(self):
        self.mock_docker.get_image = mock.Mock()
        self.driver.get_image(name='image_name')
        self.mock_docker.get_image.assert_called_once_with('image_name')

    @mock.patch('zun.image.glance.driver.GlanceDriver.delete_image_tar')
    def test_delete_image(self, mock_delete_image):
        self.mock_docker.inspect_image = mock.Mock(
            return_value={'RepoTags': ['ubuntu:1']})
        img_id = '1234'
        self.driver.delete_image(self.context, img_id, 'glance')
        self.mock_docker.inspect_image.assert_called_once_with(img_id)
        self.assertTrue(mock_delete_image.called)

    def test_load_image(self):
        self.mock_docker.load_image = mock.Mock()
        mock_open_file = mock.mock_open()
        with mock.patch('zun.container.docker.driver.open', mock_open_file):
            self.driver.load_image('test')
            self.mock_docker.load_image.assert_called_once_with(
                mock_open_file.return_value)

    def test_images(self):
        self.mock_docker.images = mock.Mock()
        self.driver.images(repo='test')
        self.mock_docker.images.assert_called_once_with('test', False)

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.common.utils.get_security_group_ids')
    @mock.patch('zun.objects.container.Container.save')
    def test_create_image_path_is_none_with_overlay2(
            self, mock_save,
            mock_get_security_group_ids,
            mock_create_or_update_port,
            mock_connect):
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        image = {'path': '', 'image': '', 'repo': 'test', 'tag': 'test'}
        mock_container = self.mock_default_container
        mock_container.status = 'Creating'
        networks = [{'network': 'fake-network'}]
        volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        # DockerDriver with supported storage driver - overlay2
        self.driver._host.sp_disk_quota = True
        self.driver._host.storage_driver = 'overlay2'
        result_container = self.driver.create(self.context, mock_container,
                                              image, networks, volumes)
        host_config = {}
        host_config['mem_limit'] = '512M'
        host_config['cpu_quota'] = 100000
        host_config['cpu_period'] = 100000
        host_config['restart_policy'] = {'Name': 'no', 'MaximumRetryCount': 0}
        host_config['runtime'] = 'runc'
        host_config['binds'] = {}
        host_config['network_mode'] = 'fake-network'
        host_config['storage_opt'] = {'size': '20G'}
        self.mock_docker.create_host_config.assert_called_once_with(
            **host_config)

        kwargs = {
            'name': '%sea8e2a25-2901-438d-8157-de7ffd68d051' %
                    consts.NAME_PREFIX,
            'command': ['fake_command'],
            'environment': {'key1': 'val1', 'key2': 'val2'},
            'working_dir': '/home/ubuntu',
            'labels': {'key1': 'val1', 'key2': 'val2'},
            'host_config': {'Id1': 'val1', 'key2': 'val2'},
            'stdin_open': True,
            'tty': True,
            'hostname': 'testhost',
            'volumes': [],
            'networking_config': {'Id': 'val1', 'key1': 'val2'},
            'mac_address': 'fake_mac',
        }
        self.mock_docker.create_container.assert_called_once_with(
            image['repo'] + ":" + image['tag'], **kwargs)
        self.assertEqual('val1', result_container.container_id)
        self.assertEqual(result_container.status,
                         consts.CREATED)

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.common.utils.get_security_group_ids')
    @mock.patch('zun.objects.container.Container.save')
    def test_create_image_path_is_none_with_devicemapper(
            self, mock_save,
            mock_get_security_group_ids,
            mock_create_or_update_port,
            mock_connect):
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        image = {'path': '', 'image': '', 'repo': 'test', 'tag': 'test'}
        mock_container = self.mock_default_container
        mock_container.status = 'Creating'
        networks = [{'network': 'fake-network'}]
        volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        # DockerDriver with supported storage driver - overlay2
        self.driver._host.sp_disk_quota = True
        self.driver._host.storage_driver = 'devicemapper'
        self.driver._host.default_base_size = 10
        result_container = self.driver.create(self.context, mock_container,
                                              image, networks, volumes)
        host_config = {}
        host_config['mem_limit'] = '512M'
        host_config['cpu_quota'] = 100000
        host_config['cpu_period'] = 100000
        host_config['restart_policy'] = {'Name': 'no', 'MaximumRetryCount': 0}
        host_config['runtime'] = 'runc'
        host_config['binds'] = {}
        host_config['network_mode'] = 'fake-network'
        host_config['storage_opt'] = {'size': '20G'}
        self.mock_docker.create_host_config.assert_called_once_with(
            **host_config)

        kwargs = {
            'name': '%sea8e2a25-2901-438d-8157-de7ffd68d051' %
                    consts.NAME_PREFIX,
            'command': ['fake_command'],
            'environment': {'key1': 'val1', 'key2': 'val2'},
            'working_dir': '/home/ubuntu',
            'labels': {'key1': 'val1', 'key2': 'val2'},
            'host_config': {'Id1': 'val1', 'key2': 'val2'},
            'stdin_open': True,
            'tty': True,
            'hostname': 'testhost',
            'volumes': [],
            'networking_config': {'Id': 'val1', 'key1': 'val2'},
            'mac_address': 'fake_mac',
        }
        self.mock_docker.create_container.assert_called_once_with(
            image['repo'] + ":" + image['tag'], **kwargs)
        self.assertEqual('val1', result_container.container_id)
        self.assertEqual(result_container.status,
                         consts.CREATED)

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.common.utils.get_security_group_ids')
    @mock.patch('zun.objects.container.Container.save')
    def test_create_docker_api_version_1_24(
            self, mock_save,
            mock_get_security_group_ids,
            mock_create_or_update_port,
            mock_connect):
        CONF.set_override("docker_remote_api_version", "1.24", "docker")
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        image = {'path': '', 'image': '', 'repo': 'test', 'tag': 'test'}
        mock_container = self.mock_default_container
        mock_container.status = 'Creating'
        mock_container.runtime = None
        networks = [{'network': 'fake-network'}]
        volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        result_container = self.driver.create(self.context, mock_container,
                                              image, networks, volumes)
        host_config = {}
        host_config['mem_limit'] = '512M'
        host_config['cpu_quota'] = 100000
        host_config['cpu_period'] = 100000
        host_config['restart_policy'] = {'Name': 'no', 'MaximumRetryCount': 0}
        host_config['runtime'] = None
        host_config['binds'] = {}
        host_config['network_mode'] = 'fake-network'
        host_config['storage_opt'] = {'size': '20G'}
        self.mock_docker.create_host_config.assert_called_once_with(
            **host_config)

        kwargs = {
            'name': '%sea8e2a25-2901-438d-8157-de7ffd68d051' %
                    consts.NAME_PREFIX,
            'command': ['fake_command'],
            'environment': {'key1': 'val1', 'key2': 'val2'},
            'working_dir': '/home/ubuntu',
            'labels': {'key1': 'val1', 'key2': 'val2'},
            'host_config': {'Id1': 'val1', 'key2': 'val2'},
            'stdin_open': True,
            'tty': True,
            'hostname': 'testhost',
            'volumes': [],
            'networking_config': {'Id': 'val1', 'key1': 'val2'},
            'mac_address': 'fake_mac',
        }
        self.mock_docker.create_container.assert_called_once_with(
            image['repo'] + ":" + image['tag'], **kwargs)
        self.assertEqual('val1', result_container.container_id)
        self.assertEqual(result_container.status,
                         consts.CREATED)

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.common.utils.get_security_group_ids')
    @mock.patch('zun.objects.container.Container.save')
    def test_create_docker_api_version_1_24_runtime_not_supported(
            self, mock_save,
            mock_get_security_group_ids,
            mock_create_or_update_port,
            mock_connect):
        CONF.set_override("docker_remote_api_version", "1.24", "docker")
        self.mock_docker.create_host_config = mock.Mock(
            return_value={'Id1': 'val1', 'key2': 'val2'})
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        image = {'path': '', 'image': '', 'repo': 'test', 'tag': 'test'}
        mock_container = self.mock_default_container
        mock_container.status = 'Creating'
        mock_container.runtime = 'runc'
        networks = [{'network': 'fake-network'}]
        volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        with self.assertRaisesRegex(
                exception.ZunException,
                "Specifying runtime in Docker API is not supported"):
            self.driver.create(self.context, mock_container,
                               image, networks, volumes)

        self.mock_docker.create_host_config.assert_not_called()
        self.mock_docker.create_container.assert_not_called()

    @mock.patch('zun.container.docker.driver.DockerDriver'
                '._cleanup_network_for_container')
    def test_delete_success(self, mock_cleanup_network_for_container):
        self.mock_docker.remove_container = mock.Mock()
        mock_container = self.mock_default_container
        self.driver.delete(self.context, mock_container, True)
        self.assertTrue(mock_cleanup_network_for_container.called)
        self.mock_docker.remove_container.assert_called_once_with(
            mock_container.container_id, force=True)

    def test_delete_fail_no_result(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.remove_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.driver.delete(self.context, mock_container, True)
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
                              self.context, mock_container,
                              True)
            self.mock_docker.remove_container.assert_called_once_with(
                mock_container.container_id, force=True)
            self.assertEqual(2, mock_init.call_count)

    def test_list(self):
        self.mock_docker.list_containers.return_value = []
        self.driver.list(self.context)
        self.mock_docker.list_containers.assert_called_once_with()

    def test_get_container_uuids(self):
        uuid = uuidutils.generate_uuid()
        uuid2 = uuidutils.generate_uuid()
        mock_container_list = [
            {'Names': ['/%s%s' % (consts.NAME_PREFIX, uuid)]},
            {'Names': ['/%s%s' % (consts.SANDBOX_NAME_PREFIX,
                                  uuidutils.generate_uuid())]},
            {'Names': ['/%s%s' % (consts.NAME_PREFIX, uuid2)]}]
        uuids = self.driver._get_container_uuids(mock_container_list)
        self.assertEqual(sorted([uuid, uuid2]), sorted(uuids))

    @mock.patch('zun.objects.container.Container.list')
    @mock.patch('zun.objects.container.Container.list_by_host')
    def test_get_local_containers(self, mock_list_by_host, mock_list):
        uuid = uuidutils.generate_uuid()
        uuid2 = uuidutils.generate_uuid()
        uuid3 = uuidutils.generate_uuid()
        mock_container = obj_utils.get_test_container(
            self.context, uuid=uuid, host='host')
        mock_container_2 = obj_utils.get_test_container(
            self.context, uuid=uuid2, host='host')
        mock_container_3 = obj_utils.get_test_container(
            self.context, uuid=uuid3, host='host2')

        def fake_container_list(context, filters):
            map = {}
            map[uuid] = mock_container
            map[uuid2] = mock_container_2
            map[uuid3] = mock_container_3
            return [map[u] for u in filters['uuid']]

        def fake_container_list_by_host(context, host):
            containers = [mock_container, mock_container_2, mock_container_3]
            return [c for c in containers if c.host == conf.CONF.host]

        mock_list.side_effect = fake_container_list
        mock_list_by_host.side_effect = fake_container_list_by_host

        # Containers in Docker matches DB records
        conf.CONF.set_override('host', 'host')
        docker_uuids = [uuid, uuid2]
        local_containers = self.driver._get_local_containers(
            self.context, docker_uuids)
        self.assertEqual(2, len(local_containers))
        self.assertIn(mock_container, local_containers)
        self.assertIn(mock_container_2, local_containers)
        self.assertNotIn(mock_container_3, local_containers)

        # Containers in Docker doesn't match DB records
        conf.CONF.set_override('host', 'host')
        docker_uuids = [uuid2, uuid3]
        local_containers = self.driver._get_local_containers(
            self.context, docker_uuids)
        self.assertEqual(3, len(local_containers))
        self.assertIn(mock_container, local_containers)
        self.assertIn(mock_container_2, local_containers)
        self.assertIn(mock_container_3, local_containers)

        # Containers are recorded in DB but missing in Docker
        conf.CONF.set_override('host', 'host')
        docker_uuids = []
        local_containers = self.driver._get_local_containers(
            self.context, docker_uuids)
        self.assertEqual(2, len(local_containers))
        self.assertIn(mock_container, local_containers)
        self.assertIn(mock_container_2, local_containers)
        self.assertNotIn(mock_container_3, local_containers)

        # Containers are present in Docker but not recorded in DB
        conf.CONF.set_override('host', 'host3')
        docker_uuids = [uuid2, uuid3]
        local_containers = self.driver._get_local_containers(
            self.context, docker_uuids)
        self.assertEqual(2, len(local_containers))
        self.assertNotIn(mock_container, local_containers)
        self.assertIn(mock_container_2, local_containers)
        self.assertIn(mock_container_3, local_containers)

    @mock.patch('zun.objects.container.Container.save')
    def test_update_containers_states(self, mock_save):
        mock_container = obj_utils.get_test_container(
            self.context, status='Running', host='host1')
        mock_container_2 = obj_utils.get_test_container(
            self.context, status='Stopped')
        conf.CONF.set_override('host', 'host2')
        with mock.patch.object(self.driver, 'list') as mock_list:
            mock_list.return_value = [mock_container_2]
            self.assertEqual(mock_container.host, 'host1')
            self.assertEqual(mock_container.status, 'Running')
            self.driver.update_containers_states(
                self.context, [mock_container])
            self.assertEqual(mock_container.host, 'host2')
            self.assertEqual(mock_container.status, 'Stopped')

    @mock.patch('zun.compute.api.API.container_rebuild')
    def test_heal_with_rebuilding_container(self, mock_container_rebuild):
        mock_container = obj_utils.get_test_container(
            self.context, status='Running',
            auto_heal=True, task_state=None)
        self.driver.heal_with_rebuilding_container(
            self.context, mock_container)
        mock_container_rebuild.assert_called_once_with(self.context,
                                                       mock_container)

    @mock.patch('zun.compute.api.API.container_rebuild')
    def test_heal_with_rebuilding_exception(self, mock_container_rebuild):
        container = Container(self.context, **utils.get_test_container())
        container.status = consts.RUNNING
        mock_container_rebuild.side_effect = Exception
        self.driver.heal_with_rebuilding_container(
            self.context, container)

    def test_show_success(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'running'})
        mock_container = mock.MagicMock()
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)

    def test_show_command(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'running',
                          'Config': {'Cmd': ['fake_command']}})
        mock_container = mock.MagicMock()
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(['fake_command'], mock_container.command)

    def test_show_without_command(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'running',
                          'Config': {'Cmd': None}})
        mock_container = mock.MagicMock()
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)
        self.assertIsNone(mock_container.command)

    def test_show_container_created(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        mock_container = mock.MagicMock()
        mock_container.status = consts.CREATING
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(consts.CREATED, mock_container.status)

    def test_show_container_create_failed(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': 'created',
                          'Config': {'Cmd': ['fake_command']}})
        mock_container = mock.MagicMock()
        mock_container.status = consts.ERROR
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(consts.ERROR, mock_container.status)

    def test_show_fail_container_id_is_none(self):
        mock_container = mock.MagicMock()
        mock_container.container_id = None
        result_container = self.driver.show(self.context, mock_container)
        self.assertIsNone(result_container.container_id)

    def test_show_fail_container_status_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock(auto_remove=False)
            result_container = self.driver.show(self.context, mock_container)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(result_container.status,
                             consts.ERROR)
            self.assertEqual(2, mock_init.call_count)

    def test_show_container_status_error_stop(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': {
                'Status': 'exited',
                'Error': 'Container start error.',
                'FinishedAt': '0001-01-01T00:00:00Z',
            }}
        )
        mock_container = mock.MagicMock()
        mock_container.status = 'existed'
        mock_container.Error = 'Container start error.'
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id
        )
        self.assertEqual(consts.STOPPED, mock_container.status)

    def test_show_container_status_error_unknown(self):
        self.mock_docker.inspect_container = mock.Mock(
            return_value={'State': {
                'Status': 'Unknown',
                'Error': 'Container run error.',
                'FinishedAt': '0001-01-01T00:00:00Z',
            }}
        )
        mock_container = mock.MagicMock()
        mock_container.status = 'UNKNOWN'
        mock_container.Error = 'Container run error.'
        self.driver.show(self.context, mock_container)
        self.mock_docker.inspect_container.assert_called_once_with(
            mock_container.container_id
        )
        self.assertEqual(consts.UNKNOWN, mock_container.status)

    def test_show_status_deleting(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock(status=consts.DELETING)
            result_container = self.driver.show(self.context, mock_container)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(result_container.status,
                             consts.DELETING)
            self.assertEqual(1, mock_init.call_count)

    def test_show_fail_api_error(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='test') as mock_init:
            self.mock_docker.inspect_container = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            mock_container = mock.MagicMock()
            self.assertRaises(errors.APIError, self.driver.show,
                              self.context, mock_container)
            self.mock_docker.inspect_container.assert_called_once_with(
                mock_container.container_id)
            self.assertEqual(1, mock_init.call_count)

    def test_reboot(self):
        self.mock_docker.restart = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.reboot(
            self.context, mock_container, '30')
        self.mock_docker.restart.assert_called_once_with(
            mock_container.container_id, timeout=30)
        self.assertEqual(result_container.status,
                         consts.RUNNING)

    def test_stop(self):
        self.mock_docker.stop = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.stop(self.context, mock_container, '30')
        self.mock_docker.stop.assert_called_once_with(
            mock_container.container_id,
            timeout=30)
        self.assertEqual(result_container.status,
                         consts.STOPPED)

    def test_start(self):
        self.mock_docker.start = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.start(self.context, mock_container)
        self.mock_docker.start.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         consts.RUNNING)

    def test_pause(self):
        self.mock_docker.pause = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.pause(self.context, mock_container)
        self.mock_docker.pause.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         consts.PAUSED)

    def test_unpause(self):
        self.mock_docker.unpause = mock.Mock()
        mock_container = mock.MagicMock()
        result_container = self.driver.unpause(self.context, mock_container)
        self.mock_docker.unpause.assert_called_once_with(
            mock_container.container_id)
        self.assertEqual(result_container.status,
                         consts.RUNNING)

    def test_show_logs(self):
        self.mock_docker.logs = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.show_logs(self.context, mock_container)
        self.mock_docker.logs.assert_called_once_with(
            mock_container.container_id, True, True, False, False,
            'all', None)

    def test_execute_create(self):
        self.mock_docker.exec_create = mock.Mock(return_value={'Id': 'test'})
        mock_container = mock.MagicMock()
        exec_id = self.driver.execute_create(
            self.context, mock_container, 'ls')
        self.assertEqual('test', exec_id)
        self.mock_docker.exec_create.assert_called_once_with(
            mock_container.container_id, 'ls', stdin=False, tty=False)

    def test_execute_run(self):
        self.mock_docker.exec_start = mock.Mock(return_value='test')
        self.mock_docker.exec_inspect = mock.Mock(
            return_value={'ExitCode': 0})
        self.driver.execute_run('test', 'ls')
        self.mock_docker.exec_start.assert_called_once_with('test', False,
                                                            False, False)
        self.mock_docker.exec_inspect.assert_called_once()

    def test_kill_successful_signal_is_none(self):
        self.mock_docker.kill = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.kill(self.context, mock_container, signal=None)
        self.mock_docker.kill.assert_called_once_with(
            mock_container.container_id)

    def test_kill_successful_signal_is_not_none(self):
        self.mock_docker.kill = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.kill(self.context, mock_container, signal='test')
        self.mock_docker.kill.assert_called_once_with(
            mock_container.container_id,
            'test')

    def test_resize(self):
        self.mock_docker.resize = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.resize(self.context, mock_container, "100", "100")
        self.mock_docker.resize.assert_called_once_with(
            mock_container.container_id, 100, 100)

    def test_commit(self):
        self.mock_docker.commit = mock.Mock()
        mock_container = mock.MagicMock()
        self.driver.commit(self.context, mock_container, "repo", "tag")
        self.mock_docker.commit.assert_called_once_with(
            mock_container.container_id, "repo", "tag")

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.container.docker.driver.DockerDriver.get_sandbox_name')
    @mock.patch('zun.common.utils.get_security_group_ids')
    def test_create_sandbox(self, mock_get_security_group_ids,
                            mock_get_sandbox_name, mock_create_or_update_port,
                            mock_connect):
        sandbox_name = 'my_test_sandbox'
        mock_get_sandbox_name.return_value = sandbox_name
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        fake_host_config = mock.Mock()
        self.mock_docker.create_host_config.return_value = fake_host_config
        mock_container = mock.MagicMock()
        hostname = 'my_hostname'
        mock_container.hostname = hostname
        requested_networks = [{'network': 'fake-network'}]
        requested_volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        result_sandbox_id = self.driver.create_sandbox(
            self.context, mock_container, requested_networks,
            requested_volumes, 'kubernetes/pause')
        self.mock_docker.create_container.assert_called_once_with(
            'kubernetes/pause', name=sandbox_name, hostname=sandbox_name,
            host_config=fake_host_config, volumes=[], mac_address='fake_mac',
            networking_config={'Id': 'val1', 'key1': 'val2'})
        self.assertEqual(result_sandbox_id, 'val1')

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.create_or_update_port')
    @mock.patch('zun.container.docker.driver.DockerDriver.get_sandbox_name')
    @mock.patch('zun.common.utils.get_security_group_ids')
    def test_create_sandbox_with_long_name(self, mock_get_security_group_ids,
                                           mock_get_sandbox_name,
                                           mock_create_or_update_port,
                                           mock_connect):
        sandbox_name = 'x' * 100
        mock_get_sandbox_name.return_value = sandbox_name
        self.mock_docker.create_container = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        self.mock_docker.create_networking_config = mock.Mock(
            return_value={'Id': 'val1', 'key1': 'val2'})
        fake_host_config = mock.Mock()
        self.mock_docker.create_host_config.return_value = fake_host_config
        mock_container = mock.MagicMock()
        mock_container.hostname = None
        requested_networks = [{'network': 'fake-network'}]
        requested_volumes = []
        fake_port = {'mac_address': 'fake_mac'}
        mock_create_or_update_port.return_value = ([], fake_port)
        result_sandbox_id = self.driver.create_sandbox(
            self.context, mock_container, requested_networks,
            requested_volumes, 'kubernetes/pause')
        self.mock_docker.create_container.assert_called_once_with(
            'kubernetes/pause', name=sandbox_name, hostname=sandbox_name[:63],
            host_config=fake_host_config, volumes=[], mac_address='fake_mac',
            networking_config={'Id': 'val1', 'key1': 'val2'})
        self.assertEqual(result_sandbox_id, 'val1')

    def test_delete_sandbox(self):
        self.mock_docker.remove_container = mock.Mock()
        mock_container = mock.MagicMock()
        mock_container.get_sandbox_id.return_value = 'test_sandbox_id'
        self.driver.delete_sandbox(self.context, mock_container)
        self.mock_docker.remove_container.assert_called_once_with(
            'test_sandbox_id', force=True)

    def test_stop_sandbox(self):
        self.mock_docker.stop = mock.Mock()
        self.driver.stop_sandbox(context=self.context,
                                 sandbox_id='test_sandbox_id')
        self.mock_docker.stop.assert_called_once_with('test_sandbox_id')

    def test_get_sandbox_name(self):
        mock_container = mock.MagicMock(
            uuid='ea8e2a25-2901-438d-8157-de7ffd68d051')
        result_sanbox_name = self.driver.get_sandbox_name(mock_container)
        self.assertEqual(
            result_sanbox_name,
            '%sea8e2a25-2901-438d-8157-de7ffd68d051' %
            consts.SANDBOX_NAME_PREFIX)

    def test_get_container_name(self):
        mock_container = mock.MagicMock(
            uuid='ea8e2a25-2901-438d-8157-de7ffd68d051')
        result_container_name = self.driver.get_container_name(
            mock_container)
        self.assertEqual(
            result_container_name,
            '%sea8e2a25-2901-438d-8157-de7ffd68d051' % consts.NAME_PREFIX)

    def test_execute_resize(self):
        self.mock_docker.exec_resize = mock.Mock()
        fake_exec_id = 'fake_id'
        self.driver.execute_resize(fake_exec_id, "100", "100")
        self.mock_docker.exec_resize.assert_called_once_with(
            fake_exec_id, height=100, width=100)

    def test_get_host_info(self):
        self.mock_docker.info = mock.Mock()
        self.mock_docker.info.return_value = {'Containers': 10,
                                              'ContainersPaused': 0,
                                              'ContainersRunning': 8,
                                              'ContainersStopped': 2,
                                              'NCPU': 48,
                                              'Architecture': 'x86_64',
                                              'OSType': 'linux',
                                              'OperatingSystem': 'CentOS',
                                              'KernelVersion': '3.10.0-123',
                                              'Labels': ['dev.type=product']}
        (total, running, paused, stopped, cpus, architecture,
         os_type, os, kernel_version, labels) = self.driver.get_host_info()
        self.assertEqual(10, total)
        self.assertEqual(8, running)
        self.assertEqual(0, paused)
        self.assertEqual(2, stopped)
        self.assertEqual(48, cpus)
        self.assertEqual('x86_64', architecture)
        self.assertEqual('linux', os_type)
        self.assertEqual('CentOS', os)
        self.assertEqual('3.10.0-123', kernel_version)
        self.assertEqual({"dev.type": "product"}, labels)

    def test_get_cpu_used(self):
        self.mock_docker.containers = mock.Mock()
        self.mock_docker.containers.return_value = [{'Id': '123456'}]
        self.mock_docker.inspect_container = mock.Mock()
        self.mock_docker.inspect_container.return_value = {
            'HostConfig': {'NanoCpus': 1.0 * 1e9,
                           'CpuPeriod': 0,
                           'CpuQuota': 0}}
        cpu_used = self.driver.get_cpu_used()
        self.assertEqual(1.0, cpu_used)

    def test_stats(self):
        self.mock_docker.stats = mock.Mock()
        mock_container = mock.MagicMock()
        self.mock_docker.stats.return_value = {
            'cpu_stats': {'cpu_usage': {'usage_in_usermode': 1000000000,
                                        'total_usage': 1000000000},
                          'system_cpu_usage': 1000000000000},
            'blkio_stats': {'io_service_bytes_recursive':
                            [{'major': 253, 'value': 10000000,
                              'minor': 4, 'op': 'Read'},
                             {'major': 253, 'value': 0,
                              'minor': 4, 'op': 'Write'},
                             {'major': 253, 'value': 0,
                              'minor': 4, 'op': 'Sync'},
                             {'major': 253, 'value': 10000000,
                              'minor': 4, 'op': 'Async'},
                             {'major': 253, 'value': 10000000,
                              'minor': 4, 'op': 'Total'}]},
            'memory_stats': {'usage': 104857600,
                             'limit': 1048576000},
            'networks': {'eth0':
                         {'tx_dropped': 0, 'rx_packets': 2, 'rx_bytes': 200,
                             'tx_errors': 0, 'rx_errors': 0, 'tx_bytes': 200,
                             'rx_dropped': 0, 'tx_packets': 2}}}
        stats_info = self.driver.stats(self.context, mock_container)
        self.assertEqual(0.1, stats_info['CPU %'])
        self.assertEqual(100, stats_info['MEM USAGE(MiB)'])
        self.assertEqual(1000, stats_info['MEM LIMIT(MiB)'])
        self.assertEqual(10, stats_info['MEM %'])
        self.assertEqual('10000000/0', stats_info['BLOCK I/O(B)'])
        self.assertEqual('200/200', stats_info['NET I/O(B)'])

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.disconnect_container_from_network')
    def test_network_detach(self, mock_detach):
        mock_container = mock.MagicMock()
        self.driver.network_detach(self.context, mock_container, 'network')
        mock_detach.assert_called_once_with(mock_container,
                                            'network',
                                            mock.ANY)

    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.disconnect_container_from_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.list_networks')
    def test_network_attach(self, mock_list, mock_disconnect, mock_connect):
        mock_container = mock.Mock()
        mock_container.security_groups = None
        mock_container.addresses = {}
        mock_list.return_value = {'network': 'network'}
        requested_network = {'network': 'network',
                             'port': '',
                             'fixed_ip': '',
                             'preserve_on_delete': False}
        self.driver.network_attach(self.context, mock_container,
                                   requested_network)
        mock_connect.assert_called_once_with(mock_container,
                                             'network',
                                             requested_network,
                                             security_groups=None)

    def test_network_attach_error(self):
        mock_container = mock.Mock()
        mock_container.security_groups = None
        mock_container.addresses = {'already-attached-net': []}
        requested_network = {'network': 'already-attached-net',
                             'port': '',
                             'fixed_ip': '',
                             'preserve_on_delete': False}
        self.assertRaises(exception.ZunException,
                          self.driver.network_attach,
                          self.context, mock_container, requested_network)

    @mock.patch('zun.common.utils.get_security_group_ids')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.connect_container_to_network')
    @mock.patch('zun.network.kuryr_network.KuryrNetwork'
                '.list_networks')
    def test_network_attach_with_security_group(self, mock_list,
                                                mock_connect,
                                                mock_get_sec_group_id):
        test_sec_group_id = '84e3a4c1-c8cd-46b1-a0d9-c8c35f6a32a4'
        mock_container = mock.Mock()
        mock_container.security_groups = ['test_sec_group']
        mock_container.addresses = {}
        mock_list.return_value = {'network': 'network'}
        mock_get_sec_group_id.return_value = test_sec_group_id
        requested_network = {'network': 'network',
                             'port': '',
                             'fixed_ip': '',
                             'preserve_on_delete': False}
        self.driver.network_attach(self.context, mock_container,
                                   requested_network)
        mock_connect.assert_called_once_with(mock_container,
                                             'network',
                                             requested_network,
                                             security_groups=test_sec_group_id)

    @mock.patch('zun.common.utils.execute')
    @mock.patch('zun.container.docker.driver.DockerDriver'
                '.get_total_disk_for_container')
    @mock.patch('zun.container.driver.ContainerDriver.get_host_mem')
    @mock.patch(
        'zun.container.docker.driver.DockerDriver.get_host_info')
    @mock.patch(
        'zun.container.docker.driver.DockerDriver.get_cpu_used')
    def test_get_available_resources(self, mock_cpu_used, mock_info, mock_mem,
                                     mock_disk, mock_output):
        self.driver = DockerDriver()
        mock_output.return_value = LSCPU_ON
        conf.CONF.set_override('floating_cpu_set', "0")
        mock_mem.return_value = (100 * units.Ki, 50 * units.Ki, 50 * units.Ki,
                                 50 * units.Ki)
        mock_info.return_value = (10, 8, 0, 2, 48, 'x86_64', 'linux',
                                  'CentOS', '3.10.0-123',
                                  {'dev.type': 'product'})
        mock_cpu_used.return_value = 1.0
        mock_disk.return_value = 80
        node_obj = objects.ComputeNode()
        self.driver.get_available_resources(node_obj)
        self.assertEqual(_numa_topo_spec, node_obj.numa_topology.to_list())
        self.assertEqual(node_obj.mem_total, 100)
        self.assertEqual(node_obj.mem_free, 50)
        self.assertEqual(node_obj.mem_available, 50)
        self.assertEqual(10, node_obj.total_containers)
        self.assertEqual(8, node_obj.running_containers)
        self.assertEqual(0, node_obj.paused_containers)
        self.assertEqual(2, node_obj.stopped_containers)
        self.assertEqual(48, node_obj.cpus)
        self.assertEqual(1.0, node_obj.cpu_used)
        self.assertEqual('x86_64', node_obj.architecture)
        self.assertEqual('linux', node_obj.os_type)
        self.assertEqual('CentOS', node_obj.os)
        self.assertEqual('3.10.0-123', node_obj.kernel_version)
        self.assertEqual({'dev.type': 'product'}, node_obj.labels)
        self.assertEqual(80, node_obj.disk_total)
