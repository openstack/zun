#    Copyright 2016 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from six import StringIO

from zun.common import consts
from zun.common import exception
from zun.compute import claims
from zun.compute import manager
import zun.conf
from zun.objects.container import Container
from zun.objects.container_action import ContainerActionEvent
from zun.objects.exec_instance import ExecInstance
from zun.objects.image import Image
from zun.objects.network import Network
from zun.objects.volume_mapping import VolumeMapping
from zun.tests import base
from zun.tests.unit.container.fake_driver import FakeDriver as fake_driver
from zun.tests.unit.db import utils


class FakeResourceTracker(object):

    def __init__(self, *args, **kwargs):
        self.compute_node = mock.MagicMock()

    def container_claim(self, context, container, pci_requests, limits):
        return claims.NopClaim()

    def container_update_claim(self, context, container, old_container,
                               limits):
        return claims.NopClaim()

    def remove_usage_from_container(self, contxt, context, is_remmoved=True):
        pass


class FakeVolumeMapping(object):

    volume_provider = 'fake_provider'
    container_path = 'fake_path'
    container_uuid = 'fake-cid'
    volume_id = 'fake-vid'

    def __init__(self):
        self.__class__.volumes = []

    def create(self, context):
        self.__class__.volumes.append(self)

    def destroy(self):
        self.__class__.volumes.remove(self)

    @classmethod
    def list_by_container(cls, context, container_id):
        return cls.volumes


class TestManager(base.TestCase):

    def setUp(self):
        super(TestManager, self).setUp()
        zun.conf.CONF.set_override(
            'container_driver',
            'zun.tests.unit.container.fake_driver.FakeDriver')
        self.compute_manager = manager.Manager()
        self.compute_manager._resource_tracker = FakeResourceTracker()

    @mock.patch.object(Container, 'save')
    def test_init_container_sets_creating_error(self, mock_save):
        container = Container(self.context, **utils.get_test_container())
        container.status = consts.CREATING
        self.compute_manager._init_container(context=self.context,
                                             container=container)
        self.assertEqual(consts.ERROR, container.status)
        self.assertIsNone(container.task_state)

    @mock.patch.object(Container, 'save')
    def test_init_container_sets_creating_tasks_error(self, mock_save):
        tasks = [consts.CONTAINER_CREATING, consts.IMAGE_PULLING]
        container = Container(self.context, **utils.get_test_container())
        for task in tasks:
            container.task_state = task
            self.compute_manager._init_container(context=self.context,
                                                 container=container)
            self.assertEqual(consts.ERROR, container.status)
            self.assertIsNone(container.task_state)

    @mock.patch.object(manager.Manager, 'container_reboot')
    @mock.patch.object(Container, 'save')
    def test_init_container_retries_reboot(self, mock_save,
                                           mock_container_reboot):
        container = Container(self.context, **utils.get_test_container())
        container.task_state = consts.CONTAINER_REBOOTING
        self.compute_manager._init_container(self.context, container)
        mock_container_reboot.assert_called_once_with(self.context,
                                                      container, 60)

    @mock.patch.object(manager.Manager, 'container_start')
    @mock.patch.object(Container, 'save')
    def test_init_container_retries_start(self, mock_save,
                                          mock_container_start):
        container = Container(self.context, **utils.get_test_container())
        container.task_state = consts.CONTAINER_STARTING
        container.status = consts.STOPPED
        self.compute_manager._init_container(self.context, container)
        mock_container_start.assert_called_once_with(self.context,
                                                     container)

    @mock.patch.object(manager.Manager, 'container_reboot')
    @mock.patch.object(Container, 'save')
    def test_container_reboot_after_host_reboot(self, mock_save,
                                                mock_container_reboot):
        container_1 = Container(self.context, **utils.get_test_container())
        container_1.status = consts.RUNNING
        self.compute_manager.restore_running_container(self.context,
                                                       container_1,
                                                       consts.STOPPED)
        mock_container_reboot.assert_called_once_with(self.context,
                                                      container_1,
                                                      10)

    @mock.patch.object(manager.Manager, 'container_stop')
    @mock.patch.object(Container, 'save')
    def test_init_container_retries_stop(self, mock_save,
                                         mock_container_stop):
        container = Container(self.context, **utils.get_test_container())
        container.task_state = consts.CONTAINER_STOPPING
        self.compute_manager._init_container(self.context, container)
        mock_container_stop.assert_called_once_with(self.context,
                                                    container, 60)

    @mock.patch.object(manager.Manager, 'container_delete')
    @mock.patch.object(Container, 'save')
    def test_init_container_retries_deleting(self, mock_save,
                                             mock_container_delete):
        kw = {'status': consts.DELETING,
              'task_state': None}
        container = Container(self.context, **utils.get_test_container(**kw))
        self.compute_manager._init_container(self.context, container)
        mock_container_delete.assert_called_once_with(self.context, container,
                                                      force=True)

    @mock.patch.object(manager.Manager, 'container_delete')
    @mock.patch.object(Container, 'save')
    def test_init_container_retries_container_delete_task(
            self, mock_save, mock_container_delete):
        container = Container(self.context, **utils.get_test_container())
        container.task_state = consts.CONTAINER_DELETING
        self.compute_manager._init_container(self.context, container)
        mock_container_delete.assert_called_once_with(self.context, container,
                                                      force=True)

    @mock.patch.object(Container, 'save')
    def test_fail_container(self, mock_save):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._fail_container(self.context, container,
                                             "Creation Failed")
        self.assertEqual(consts.ERROR, container.status)
        self.assertEqual("Creation Failed", container.status_reason)
        self.assertIsNone(container.task_state)

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'create')
    def test_container_create(self, mock_create, mock_pull, mock_save,
                              mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = image, False
        self.compute_manager._resource_tracker = FakeResourceTracker()
        networks = []
        volumes = []
        self.compute_manager._do_container_create(self.context, container,
                                                  networks, volumes)
        mock_save.assert_called_with(self.context)
        mock_pull.assert_any_call(self.context, container.image, '',
                                  'always', 'glance')
        mock_create.assert_called_once_with(self.context, container, image,
                                            networks, volumes)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_create'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_docker_error(
            self, mock_fail, mock_pull, mock_save, mock_event_finish,
            mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.DockerError("Pull Failed")
        networks = []
        volumes = []
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_create,
                          self.context, container, networks, volumes)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Pull Failed")
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_create'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_image_not_found(
            self, mock_fail, mock_pull, mock_save, mock_event_finish,
            mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ImageNotFound("Image Not Found")
        networks = []
        volumes = []
        self.assertRaises(exception.ImageNotFound,
                          self.compute_manager._do_container_create,
                          self.context, container, networks, volumes)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Image Not Found")
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_create'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_zun_exception(
            self, mock_fail, mock_pull, mock_save, mock_event_finish,
            mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ZunException(
            message="Image Not Found")
        networks = []
        volumes = []
        self.assertRaises(
            exception.ZunException,
            self.compute_manager._do_container_create,
            self.context, container, networks, volumes)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Image Not Found")
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_create'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_docker_create_failed(
            self, mock_fail, mock_create, mock_pull, mock_save,
            mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance',
                 'repo': 'test', 'tag': 'testtag'}
        mock_pull.return_value = image, False
        mock_create.side_effect = exception.DockerError("Creation Failed")
        self.compute_manager._resource_tracker = FakeResourceTracker()
        networks = []
        volumes = []
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_create,
                          self.context, container, networks, volumes)
        mock_fail.assert_called_once_with(
            self.context, container, "Creation Failed", unset_host=True)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_create'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'start')
    def test_container_run(
            self, mock_start, mock_create,
            mock_is_volume_available, mock_attach_volume,
            mock_detach_volume, mock_pull, mock_list_by_container, mock_save,
            mock_spawn_n, mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_create.return_value = container
        mock_pull.return_value = image, False
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        container.status = 'Stopped'
        self.compute_manager._resource_tracker = FakeResourceTracker()
        networks = []
        volumes = [FakeVolumeMapping()]
        self.compute_manager.container_create(
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        mock_pull.assert_any_call(self.context, container.image, '',
                                  'always', 'glance')
        mock_create.assert_called_once_with(self.context, container, image,
                                            networks, volumes)
        mock_start.assert_called_once_with(self.context, container)
        mock_attach_volume.assert_called_once()
        mock_detach_volume.assert_not_called()
        mock_is_volume_available.assert_called_once()
        self.assertEqual(1, len(FakeVolumeMapping.volumes))

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'start')
    def test_container_run_driver_attach_failed(
            self, mock_start, mock_create,
            mock_is_volume_available, mock_attach_volume,
            mock_detach_volume, mock_pull, mock_list_by_container, mock_save,
            mock_spawn_n, mock_event_finish, mock_event_start):
        mock_is_volume_available.return_value = True
        mock_attach_volume.side_effect = [None, base.TestingException("fake")]
        container = Container(self.context, **utils.get_test_container())
        vol = FakeVolumeMapping()
        vol2 = FakeVolumeMapping()
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_create.return_value = container
        mock_pull.return_value = image, False
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        container.status = 'Stopped'
        self.compute_manager._resource_tracker = FakeResourceTracker()
        networks = []
        volumes = [vol, vol2]
        self.assertRaises(
            base.TestingException,
            self.compute_manager.container_create,
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        mock_pull.assert_not_called()
        mock_create.assert_not_called()
        mock_start.assert_not_called()
        mock_attach_volume.assert_has_calls([
            mock.call(mock.ANY, vol), mock.call(mock.ANY, vol2)])
        mock_detach_volume.assert_has_calls([
            mock.call(mock.ANY, vol)])
        self.assertEqual(0, len(FakeVolumeMapping.volumes))

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_container_run_image_not_found(
            self, mock_pull, mock_is_volume_available,
            mock_attach_volume, mock_detach_volume,
            mock_list_by_container, mock_save, mock_spawn_n, mock_event_finish,
            mock_event_start):
        container_dict = utils.get_test_container(
            image='test:latest', image_driver='docker',
            image_pull_policy='ifnotpresent')
        container = Container(self.context, **container_dict)
        mock_pull.side_effect = exception.ImageNotFound(
            message="Image Not Found")
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        networks = []
        volumes = [FakeVolumeMapping()]
        self.assertRaises(
            exception.ImageNotFound,
            self.compute_manager.container_create,
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        self.assertEqual('Error', container.status)
        self.assertEqual('Image Not Found', container.status_reason)
        mock_pull.assert_called_once_with(self.context, 'test', 'latest',
                                          'ifnotpresent', 'docker')
        mock_attach_volume.assert_called_once()
        mock_detach_volume.assert_called_once()
        mock_is_volume_available.assert_called_once()
        self.assertEqual(0, len(FakeVolumeMapping.volumes))

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_container_run_image_pull_exception_raised(
            self, mock_pull, mock_is_volume_available,
            mock_attach_volume, mock_detach_volume,
            mock_list_by_container, mock_save, mock_spawn_n, mock_event_finish,
            mock_event_start):
        container_dict = utils.get_test_container(
            image='test:latest', image_driver='docker',
            image_pull_policy='ifnotpresent')
        container = Container(self.context, **container_dict)
        mock_pull.side_effect = exception.ZunException(
            message="Image Not Found")
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        networks = []
        volumes = [FakeVolumeMapping()]
        self.assertRaises(
            exception.ZunException,
            self.compute_manager.container_create,
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        self.assertEqual('Error', container.status)
        self.assertEqual('Image Not Found', container.status_reason)
        mock_pull.assert_called_once_with(self.context, 'test', 'latest',
                                          'ifnotpresent', 'docker')
        mock_attach_volume.assert_called_once()
        mock_detach_volume.assert_called_once()
        mock_is_volume_available.assert_called_once()
        self.assertEqual(0, len(FakeVolumeMapping.volumes))

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_container_run_image_pull_docker_error(
            self, mock_pull, mock_is_volume_available,
            mock_attach_volume, mock_detach_volume,
            mock_list_by_container, mock_save, mock_spawn_n, mock_event_finish,
            mock_event_start):
        container_dict = utils.get_test_container(
            image='test:latest', image_driver='docker',
            image_pull_policy='ifnotpresent')
        container = Container(self.context, **container_dict)
        mock_pull.side_effect = exception.DockerError(
            message="Docker Error occurred")
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        networks = []
        volumes = [FakeVolumeMapping()]
        self.assertRaises(
            exception.DockerError,
            self.compute_manager.container_create,
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        self.assertEqual('Error', container.status)
        self.assertEqual('Docker Error occurred', container.status_reason)
        mock_pull.assert_called_once_with(self.context, 'test', 'latest',
                                          'ifnotpresent', 'docker')
        mock_attach_volume.assert_called_once()
        mock_detach_volume.assert_called_once()
        mock_is_volume_available.assert_called_once()
        self.assertEqual(0, len(FakeVolumeMapping.volumes))

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.common.utils.spawn_n')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container',
                       side_effect=FakeVolumeMapping.list_by_container)
    @mock.patch.object(fake_driver, 'detach_volume')
    @mock.patch.object(fake_driver, 'attach_volume')
    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'create')
    def test_container_run_create_raises_docker_error(
            self, mock_create, mock_pull, mock_is_volume_available,
            mock_attach_volume, mock_detach_volume,
            mock_list_by_container, mock_save, mock_spawn_n,
            mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance',
                 'repo': 'test', 'tag': 'testtag'}
        mock_pull.return_value = image, True
        mock_create.side_effect = exception.DockerError(
            message="Docker Error occurred")
        mock_spawn_n.side_effect = lambda f, *x, **y: f(*x, **y)
        self.compute_manager._resource_tracker = FakeResourceTracker()
        networks = []
        volumes = [FakeVolumeMapping()]
        self.assertRaises(
            exception.DockerError,
            self.compute_manager.container_create,
            self.context,
            requested_networks=networks,
            requested_volumes=volumes,
            container=container,
            limits=None, run=True)
        mock_save.assert_called_with(self.context)
        self.assertEqual('Error', container.status)
        self.assertEqual('Docker Error occurred', container.status_reason)
        mock_pull.assert_any_call(self.context, container.image, '',
                                  'always', 'glance')
        mock_create.assert_called_once_with(
            self.context, container, image, networks, volumes)
        mock_attach_volume.assert_called_once()
        mock_detach_volume.assert_called_once()
        mock_is_volume_available.assert_called_once()
        self.assertEqual(0, len(FakeVolumeMapping.volumes))

    @mock.patch.object(FakeResourceTracker,
                       'remove_usage_from_container')
    @mock.patch.object(Container, 'destroy')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete(
            self, mock_delete, mock_list_by_container, mock_save,
            mock_cnt_destroy, mock_remove_usage):
        mock_list_by_container.return_value = []
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_delete(self. context, container,
                                                  False)
        mock_save.assert_called_with(self.context)
        mock_delete.assert_called_once_with(self.context, container, False)
        mock_cnt_destroy.assert_called_once_with(self.context)
        mock_remove_usage.assert_called_once_with(self.context, container,
                                                  True)

    @mock.patch.object(FakeResourceTracker,
                       'remove_usage_from_container')
    @mock.patch.object(Container, 'destroy')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_failed(self, mock_delete, mock_save,
                                     mock_fail, mock_destroy,
                                     mock_remove_usage):
        container = Container(self.context, **utils.get_test_container())
        mock_delete.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_delete,
                          self.context, container, False)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Docker Error occurred')
        mock_destroy.assert_not_called()
        mock_remove_usage.assert_not_called()

    @mock.patch.object(FakeResourceTracker,
                       'remove_usage_from_container')
    @mock.patch.object(Container, 'destroy')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_failed_force(self, mock_delete,
                                           mock_list_by_container,
                                           mock_save,
                                           mock_fail, mock_destroy,
                                           mock_remove_usage):
        mock_list_by_container.return_value = []
        container = Container(self.context, **utils.get_test_container())
        mock_delete.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_delete(self.context, container,
                                                  True)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Docker Error occurred')
        mock_destroy.assert_called_once_with(self.context)
        mock_remove_usage.assert_called_once_with(self.context, container,
                                                  True)

    @mock.patch.object(FakeResourceTracker,
                       'remove_usage_from_container')
    @mock.patch.object(Container, 'destroy')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(manager.Manager, '_delete_sandbox')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_sandbox_failed(self, mock_delete, mock_save,
                                             mock_delete_sandbox,
                                             mock_fail, mock_destroy,
                                             mock_remove_usage):
        self.compute_manager.use_sandbox = True
        container = Container(self.context, **utils.get_test_container())
        container.set_sandbox_id("sandbox_id")
        mock_delete_sandbox.side_effect = exception.ZunException(
            message="Unexpected exception")
        self.assertRaises(exception.ZunException,
                          self.compute_manager._do_container_delete,
                          self.context, container, False)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Unexpected exception')
        mock_destroy.assert_not_called()
        mock_remove_usage.assert_not_called()

    @mock.patch.object(FakeResourceTracker,
                       'remove_usage_from_container')
    @mock.patch.object(Container, 'destroy')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(manager.Manager, '_delete_sandbox')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(VolumeMapping, 'list_by_container')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_sandbox_failed_force(self, mock_delete,
                                                   mock_list_by_container,
                                                   mock_save,
                                                   mock_delete_sandbox,
                                                   mock_fail, mock_destroy,
                                                   mock_remove_usage):
        mock_list_by_container.return_value = []
        self.compute_manager.use_sandbox = True
        container = Container(self.context, **utils.get_test_container())
        container.set_sandbox_id("sandbox_id")
        mock_delete_sandbox.side_effect = exception.ZunException(
            message="Unexpected exception")
        self.compute_manager._do_container_delete(self.context, container,
                                                  True)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Unexpected exception')

    @mock.patch.object(fake_driver, 'show')
    def test_container_show(self, mock_show):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_show(self.context, container)
        mock_show.assert_called_once_with(self.context, container)

    @mock.patch.object(fake_driver, 'show')
    def test_container_show_failed(self, mock_show):
        container = Container(self.context, **utils.get_test_container())
        mock_show.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_show,
                          self.context, container)

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.compute.manager.Manager._get_vol_info')
    @mock.patch('zun.compute.manager.Manager._get_network_info')
    @mock.patch.object(fake_driver, 'pull_image')
    @mock.patch.object(fake_driver, 'check_container_exist')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_rebuild(self, mock_delete, mock_create,
                               mock_save, mock_check, mock_pull,
                               mock_get_network_info, mock_get_vol_info,
                               mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = image, False
        container.status = 'Created'
        mock_get_network_info.return_value = []
        mock_get_vol_info.return_value = []
        mock_check.return_value = True
        self.compute_manager._do_container_rebuild(self.context, container)
        mock_save.assert_called_with(self.context)
        self.assertTrue(mock_create.called)
        mock_delete.assert_called_once_with(self.context, container, True)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_rebuild'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch('zun.compute.manager.Manager._get_vol_info')
    @mock.patch('zun.compute.manager.Manager._get_network_info')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_rebuild_failed(
            self, mock_fail, mock_get_network_info, mock_get_vol_info,
            mock_event_finish, mock_event_start):
        mock_get_vol_info.return_value = []
        fake_exc = exception.PortNotFound(port='fake-port')
        mock_get_network_info.side_effect = fake_exc
        container = Container(self.context, **utils.get_test_container())
        self.assertRaises(exception.PortNotFound,
                          self.compute_manager._do_container_rebuild,
                          self.context, container)
        mock_fail.assert_called_with(self.context,
                                     container, str(fake_exc))
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_rebuild'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot(self, mock_reboot, mock_save, mock_event_finish,
                              mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_reboot(self.context, container, 10)
        mock_save.assert_called_with(self.context)
        mock_reboot.assert_called_once_with(self.context, container, 10)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_reboot'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot_failed(self, mock_reboot, mock_save,
                                     mock_event_finish,
                                     mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_reboot.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_reboot(self.context, container, 10)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_reboot'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop(self, mock_stop, mock_save, mock_event_finish,
                            mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_stop(self.context, container, 10)
        mock_save.assert_called_with(self.context)
        mock_stop.assert_called_once_with(self.context, container, 10)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_stop'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop_failed(self, mock_stop, mock_save,
                                   mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_stop.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_stop(self.context, container, 10)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_stop'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'start')
    def test_container_start(self, mock_start, mock_save, mock_event_finish,
                             mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_start(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_start.assert_called_once_with(self.context, container)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_start'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(fake_driver, 'start')
    def test_container_start_failed(self, mock_start,
                                    mock_fail, mock_save, mock_event_finish,
                                    mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_start.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_start,
                          self.context, container)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Docker Error occurred')
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_start'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause(self, mock_pause, mock_save,
                             mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_pause(self.context, container)
        mock_pause.assert_called_once_with(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_pause'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause_failed(self, mock_pause, mock_save,
                                    mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_pause.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_pause(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_pause'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause(self, mock_unpause, mock_save,
                               mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_unpause(self.context, container)
        mock_unpause.assert_called_once_with(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_unpause'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause_failed(self, mock_unpause, mock_save,
                                      mock_event_finish,
                                      mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_unpause.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_unpause(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_unpause'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_logs(self.context,
                                            container, True, True,
                                            False, 'all', None)
        mock_logs.assert_called_once_with(
            self.context, container, stderr=True, stdout=True,
            timestamps=False, tail='all', since=None)

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs_failed(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        mock_logs.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_logs,
                          self.context, container, True, True,
                          False, 'all', None)

    @mock.patch.object(fake_driver, 'execute_run')
    @mock.patch.object(fake_driver, 'execute_create')
    def test_container_execute(self, mock_execute_create, mock_execute_run):
        mock_execute_create.return_value = 'fake_exec_id'
        mock_execute_run.return_value = 'fake_output', 'fake_exit_code'
        container = Container(self.context, **utils.get_test_container())
        result = self.compute_manager.container_exec(
            self.context, container, 'fake_cmd', True, False)
        self.assertEqual('fake_output', result.get('output'))
        self.assertEqual('fake_exit_code', result.get('exit_code'))
        self.assertIsNone(result.get('exec_id'))
        self.assertIsNone(result.get('token'))
        mock_execute_create.assert_called_once_with(
            self.context, container, 'fake_cmd', False)
        mock_execute_run.assert_called_once_with('fake_exec_id', 'fake_cmd')

    @mock.patch.object(ExecInstance, 'create')
    @mock.patch.object(fake_driver, 'execute_run')
    @mock.patch.object(fake_driver, 'execute_create')
    def test_container_execute_interactive(
            self, mock_execute_create, mock_execute_run, mock_create):
        mock_execute_create.return_value = 'fake_exec_id'
        container = Container(self.context, **utils.get_test_container())
        result = self.compute_manager.container_exec(
            self.context, container, 'fake_cmd', False, True)
        self.assertIsNone(result.get('output'))
        self.assertIsNone(result.get('exit_code'))
        self.assertEqual('fake_exec_id', result.get('exec_id'))
        self.assertIsNotNone(result.get('token'))
        mock_execute_create.assert_called_once_with(
            self.context, container, 'fake_cmd', True)
        mock_execute_run.assert_not_called()

    @mock.patch.object(fake_driver, 'execute_create')
    def test_container_execute_failed(self, mock_execute_create):
        container = Container(self.context, **utils.get_test_container())
        mock_execute_create.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_exec,
                          self.context, container, 'fake_cmd', True, False)

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'kill')
    def test_container_kill(self, mock_kill, mock_save,
                            mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_kill(self.context, container, None)
        mock_kill.assert_called_once_with(self.context, container, None)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_kill'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'kill')
    def test_container_kill_failed(self, mock_kill, mock_save,
                                   mock_event_finish,
                                   mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_kill.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_kill(self.context, container, None)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_kill'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'update')
    def test_container_update(self, mock_update, mock_save):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_update(self.context, container,
                                              {'memory': 512})
        mock_save.assert_called_with(self.context)
        mock_update.assert_called_once_with(self.context, container)

    @mock.patch.object(fake_driver, 'update')
    def test_container_update_failed(self, mock_update):
        container = Container(self.context, **utils.get_test_container())
        mock_update.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_update,
                          self.context, container, {})

    @mock.patch.object(fake_driver, 'get_websocket_url')
    @mock.patch.object(Container, 'save')
    def test_container_attach_successful(self, mock_save,
                                         mock_get_websocket_url):
        container = Container(self.context, **utils.get_test_container())
        mock_get_websocket_url.return_value = "ws://test"
        self.compute_manager.container_attach(self.context, container)
        mock_get_websocket_url.assert_called_once_with(self.context, container)
        mock_save.assert_called_once_with(self.context)

    @mock.patch.object(fake_driver, 'get_websocket_url')
    def test_container_attach_failed(self, mock_get_websocket_url):
        container = Container(self.context, **utils.get_test_container())
        mock_get_websocket_url.side_effect = Exception
        self.assertRaises(exception.ZunException,
                          self.compute_manager.container_attach,
                          self.context, container)

    @mock.patch.object(fake_driver, 'resize')
    def test_container_resize(self, mock_resize):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_resize(
            self.context, container, "100", "100")
        mock_resize.assert_called_once_with(
            self.context, container, "100", "100")

    @mock.patch.object(fake_driver, 'resize')
    def test_container_resize_failed(self, mock_resize):
        container = Container(self.context, **utils.get_test_container())
        mock_resize.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_resize,
                          self.context, container, "100", "100")

    @mock.patch.object(fake_driver, 'inspect_image')
    @mock.patch.object(Image, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_image_pull(self, mock_pull, mock_save, mock_inspect):
        image = Image(self.context, **utils.get_test_image())
        ret = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = ret, True
        mock_inspect.return_value = {'Id': 'fake-id', 'Size': 512}
        self.compute_manager._do_image_pull(self.context, image)
        mock_pull.assert_any_call(self.context, image.repo, image.tag)
        mock_save.assert_called_once()
        mock_inspect.assert_called_once_with(image.repo + ":" + image.tag)

    @mock.patch.object(fake_driver, 'load_image')
    @mock.patch.object(fake_driver, 'inspect_image')
    @mock.patch.object(Image, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_image_pull_not_loaded(self, mock_pull, mock_save,
                                   mock_inspect, mock_load):
        image = Image(self.context, **utils.get_test_image())
        repo_tag = image.repo + ":" + image.tag
        ret = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = ret, False
        mock_inspect.return_value = {'Id': 'fake-id', 'Size': 512}
        self.compute_manager._do_image_pull(self.context, image)
        mock_pull.assert_any_call(self.context, image.repo, image.tag)
        mock_save.assert_called_once()
        mock_inspect.assert_called_once_with(repo_tag)
        mock_load.assert_called_once_with(ret['path'])

    @mock.patch.object(fake_driver, 'inspect_image')
    @mock.patch.object(Image, 'save')
    @mock.patch.object(fake_driver, 'pull_image')
    def test_image_pull_tag_is_none(self, mock_pull, mock_save, mock_inspect):
        image = Image(self.context, **utils.get_test_image(tag=None))
        ret = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = ret, True
        mock_inspect.return_value = {'Id': 'fake-id', 'Size': 512}
        self.compute_manager._do_image_pull(self.context, image)
        mock_pull.assert_any_call(self.context, image.repo, image.tag)
        mock_save.assert_called_once()
        mock_inspect.assert_called_once_with(image.repo)

    @mock.patch.object(fake_driver, 'execute_resize')
    def test_container_exec_resize(self, mock_resize):
        self.compute_manager.container_exec_resize(
            self.context, 'fake_exec_id', "100", "100")
        mock_resize.assert_called_once_with('fake_exec_id', "100", "100")

    @mock.patch.object(fake_driver, 'execute_resize')
    def test_container_exec_resize_failed(self, mock_resize):
        mock_resize.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_exec_resize,
                          self.context, 'fake_exec_id', "100", "100")

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(fake_driver, 'upload_image_data')
    @mock.patch.object(fake_driver, 'get_image')
    @mock.patch.object(fake_driver, 'commit')
    @mock.patch.object(fake_driver, 'pause')
    @mock.patch.object(fake_driver, 'unpause')
    @mock.patch.object(Container, 'save')
    def test_container_commit(
            self, mock_save, mock_unpause, mock_pause, mock_commit,
            mock_get_image, mock_upload_image_data, mock_event_finish,
            mock_event_start):
        container = Container(self.context, **utils.get_test_container(
            status=consts.PAUSED))
        mock_get_image_response = mock.MagicMock()
        mock_get_image_response.data = StringIO().read()
        mock_get_image.return_value = mock_get_image_response
        mock_upload_image_data.return_value = mock.MagicMock()

        self.compute_manager._do_container_commit(self.context,
                                                  mock_get_image_response,
                                                  container, 'repo', 'tag')
        mock_commit.assert_called_once_with(
            self.context, container, 'repo', 'tag')
        mock_pause.assert_not_called()
        mock_unpause.assert_not_called()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_commit'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(fake_driver, 'upload_image_data')
    @mock.patch.object(fake_driver, 'get_image')
    @mock.patch.object(fake_driver, 'commit')
    @mock.patch.object(fake_driver, 'pause')
    @mock.patch.object(fake_driver, 'unpause')
    @mock.patch.object(Container, 'save')
    def test_container_commit_with_pause(
            self, mock_save, mock_unpause, mock_pause, mock_commit,
            mock_get_image, mock_upload_image_data, mock_event_finish,
            mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_get_image_response = mock.MagicMock()
        mock_get_image_response.data = StringIO().read()
        mock_get_image.return_value = mock_get_image_response
        mock_upload_image_data.return_value = mock.MagicMock()
        mock_unpause.return_value = container
        mock_pause.return_value = container

        self.compute_manager._do_container_commit(self.context,
                                                  mock_get_image_response,
                                                  container, 'repo', 'tag')
        mock_commit.assert_called_once_with(
            self.context, container, 'repo', 'tag')
        mock_pause.assert_called_once_with(self.context, container)
        mock_unpause.assert_called_once_with(self.context, container)
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_commit'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(fake_driver, 'delete_committed_image')
    @mock.patch.object(fake_driver, 'commit')
    @mock.patch.object(fake_driver, 'pause')
    @mock.patch.object(fake_driver, 'unpause')
    @mock.patch.object(Container, 'save')
    def test_container_commit_failed(self, mock_save, mock_unpause, mock_pause,
                                     mock_commit, mock_delete,
                                     mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        mock_get_image_response = mock.MagicMock()
        mock_get_image_response.data = StringIO().read()
        mock_commit.side_effect = exception.DockerError
        mock_unpause.return_value = container
        mock_pause.return_value = container
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_commit,
                          self.context, mock_get_image_response, container,
                          'repo', 'tag')
        self.assertTrue(mock_delete.called)
        mock_commit.assert_called_once_with(
            self.context, container, 'repo', 'tag')
        mock_pause.assert_called_once_with(self.context, container)
        mock_unpause.assert_called_once_with(self.context, container)
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_container_commit'),
            mock_event_finish.call_args[0])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNotNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'network_detach')
    def test_container_network_detach(self, mock_detach, mock_save,
                                      mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_network_detach(self.context, container,
                                                'network')
        mock_detach.assert_called_once_with(self.context, container, mock.ANY)
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_network_detach'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(ContainerActionEvent, 'event_start')
    @mock.patch.object(ContainerActionEvent, 'event_finish')
    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'network_attach')
    def test_container_network_attach(self, mock_attach, mock_save,
                                      mock_event_finish, mock_event_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_network_attach(self.context, container,
                                                'network')
        mock_save.assert_called_with(self.context)
        mock_event_start.assert_called_once()
        mock_event_finish.assert_called_once()
        self.assertEqual(
            (self.context, container.uuid, 'compute__do_network_attach'),
            mock_event_finish.call_args[0])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_val'])
        self.assertIsNone(mock_event_finish.call_args[1]['exc_tb'])

    @mock.patch.object(fake_driver, 'is_volume_available')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_wait_for_volumes_available(self, mock_fail,
                                        mock_is_volume_available):
        mock_is_volume_available.return_value = True
        container = Container(self.context, **utils.get_test_container())
        volumes = [FakeVolumeMapping()]
        self.compute_manager._wait_for_volumes_available(self.context,
                                                         volumes,
                                                         container)
        mock_is_volume_available.assert_called_once()
        mock_fail.assert_not_called()

    @mock.patch.object(Network, 'save')
    @mock.patch.object(fake_driver, 'create_network')
    def test_network_create(self, mock_create, mock_save):
        network = Network(self.context, **utils.get_test_network())
        ret = ({'Id': '0eeftestnetwork'})
        mock_create.return_value = ret
        self.compute_manager.network_create(self.context, network)
        mock_create.assert_any_call(self.context, network)
        mock_save.assert_called_once()
