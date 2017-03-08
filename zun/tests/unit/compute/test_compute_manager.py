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


from zun.common import exception
from zun.compute import manager
import zun.conf
from zun.objects.container import Container
from zun.objects import fields
from zun.tests import base
from zun.tests.unit.container.fake_driver import FakeDriver as fake_driver
from zun.tests.unit.db import utils


class TestManager(base.TestCase):

    def setUp(self):
        super(TestManager, self).setUp()
        zun.conf.CONF.set_override(
            'container_driver',
            'zun.tests.unit.container.fake_driver.FakeDriver')
        self.compute_manager = manager.Manager()

    @mock.patch.object(Container, 'save')
    def test_fail_container(self, mock_save):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._fail_container(self.context, container,
                                             "Creation Failed")
        self.assertEqual(fields.ContainerStatus.ERROR, container.status)
        self.assertEqual("Creation Failed", container.status_reason)
        self.assertIsNone(container.task_state)

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'create_sandbox')
    def test_container_create(self, mock_create_sandbox, mock_create,
                              mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = image
        mock_create_sandbox.return_value = 'fake_id'
        self.compute_manager._do_container_create(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_pull.assert_any_call(self.context, container.image, 'latest',
                                  'always', 'glance')
        mock_create.assert_called_once_with(self.context, container,
                                            'fake_id', image)

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'create_sandbox')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_docker_error(
            self, mock_fail, mock_pull, mock_create_sandbox, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.DockerError("Pull Failed")
        mock_create_sandbox.return_value = mock.MagicMock()
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Pull Failed")

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'create_sandbox')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_image_not_found(
            self, mock_fail, mock_pull, mock_create_sandbox, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ImageNotFound("Image Not Found")
        mock_create_sandbox.return_value = mock.MagicMock()
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Image Not Found")

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'create_sandbox')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed_zun_exception(
            self, mock_fail, mock_pull, mock_create_sandbox, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ZunException(
            message="Image Not Found")
        mock_create_sandbox.return_value = mock.MagicMock()
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Image Not Found")

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'create_sandbox')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_docker_create_failed(self, mock_fail,
                                                   mock_create_sandbox,
                                                   mock_create, mock_pull,
                                                   mock_save):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_pull.return_value = image
        mock_create.side_effect = exception.DockerError("Creation Failed")
        mock_create_sandbox.return_value = mock.MagicMock()
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(self.context,
                                          container, "Creation Failed")

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(fake_driver, 'start')
    def test_container_run(self, mock_start,
                           mock_create, mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        image = {'image': 'repo', 'path': 'out_path', 'driver': 'glance'}
        mock_create.return_value = container
        mock_pull.return_value = image
        container.status = 'Stopped'
        self.compute_manager._do_container_run(self.context, container)
        mock_save.assert_called_with(self.context)
        mock_pull.assert_any_call(self.context, container.image, 'latest',
                                  'always', 'glance')
        mock_create.assert_called_once_with(self.context, container,
                                            None, image)
        mock_start.assert_called_once_with(container)

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_run_image_not_found(self, mock_fail,
                                           mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ImageNotFound(
            message="Image Not Found")
        self.compute_manager._do_container_run(self.context,
                                               container)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Image Not Found')
        mock_pull.assert_called_once_with(self.context, 'kubernetes/pause',
                                          'latest', 'ifnotpresent', 'docker')

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_run_image_pull_exception_raised(self, mock_fail,
                                                       mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.ZunException(
            message="Image Not Found")
        self.compute_manager._do_container_run(self.context,
                                               container)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Image Not Found')
        mock_pull.assert_called_once_with(self.context, 'kubernetes/pause',
                                          'latest', 'ifnotpresent', 'docker')

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_run_image_pull_docker_error(self, mock_fail,
                                                   mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_run(self.context,
                                               container)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Docker Error occurred')
        mock_pull.assert_called_once_with(self.context, 'kubernetes/pause',
                                          'latest', 'ifnotpresent', 'docker')

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(fake_driver, 'create')
    def test_container_run_create_raises_docker_error(self, mock_create,
                                                      mock_fail,
                                                      mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.return_value = {'name': 'nginx', 'path': None}
        mock_create.side_effect = exception.DockerError(
            message="Docker Error occurred")
        self.compute_manager._do_container_run(self.context,
                                               container)
        mock_save.assert_called_with(self.context)
        mock_fail.assert_called_with(self.context,
                                     container, 'Docker Error occurred')
        mock_pull.assert_any_call(self.context, container.image, 'latest',
                                  'always', 'glance')
        mock_create.assert_called_once_with(self.context, container, None,
                                            {'name': 'nginx', 'path': None})

    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete(self, mock_delete):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_delete(self. context, container, False)
        mock_delete.assert_called_once_with(container, False)

    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_failed(self, mock_delete):
        container = Container(self.context, **utils.get_test_container())
        mock_delete.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_delete,
                          self.context, container, False)

    @mock.patch.object(fake_driver, 'list')
    def test_container_list(self, mock_list):
        self.compute_manager.container_list(self.context)
        mock_list.assert_called_once_with()

    @mock.patch.object(fake_driver, 'list')
    def test_container_list_failed(self, mock_list):
        mock_list.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_list,
                          self.context)

    @mock.patch.object(fake_driver, 'show')
    def test_container_show(self, mock_show):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_show(self.context, container)
        mock_show.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'show')
    def test_container_show_failed(self, mock_show):
        container = Container(self.context, **utils.get_test_container())
        mock_show.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_show,
                          self.context, container)

    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot(self, mock_reboot):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_reboot(self.context, container, 10)
        mock_reboot.assert_called_once_with(container, 10)

    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot_failed(self, mock_reboot):
        container = Container(self.context, **utils.get_test_container())
        mock_reboot.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_reboot,
                          self.context, container, 10, reraise=True)

    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop(self, mock_stop):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_stop(self.context, container, 10)
        mock_stop.assert_called_once_with(container, 10)

    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop_failed(self, mock_stop):
        container = Container(self.context, **utils.get_test_container())
        mock_stop.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_stop,
                          self.context, container, 10, reraise=True)

    @mock.patch.object(fake_driver, 'start')
    def test_container_start(self, mock_start):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_start(self.context, container)
        mock_start.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_fail_container')
    @mock.patch.object(fake_driver, 'start')
    def test_container_start_failed(self, mock_start,
                                    mock_fail):
        container = Container(self.context, **utils.get_test_container())
        mock_start.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_start,
                          self.context, container, reraise=True)
        mock_fail.assert_called_once()

    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause(self, mock_pause):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_pause(self.context, container)
        mock_pause.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause_failed(self, mock_pause):
        container = Container(self.context, **utils.get_test_container())
        mock_pause.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_pause,
                          self.context, container, reraise=True)

    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause(self, mock_unpause):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_unpause(self.context, container)
        mock_unpause.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause_failed(self, mock_unpause):
        container = Container(self.context, **utils.get_test_container())
        mock_unpause.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_unpause,
                          self.context, container, reraise=True)

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_logs(self.context,
                                            container, True, True,
                                            False, 'all', None)
        mock_logs.assert_called_once_with(container, stderr=True, stdout=True,
                                          timestamps=False, tail='all',
                                          since=None)

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs_failed(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        mock_logs.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_logs,
                          self.context, container, True, True,
                          False, 'all', None)

    @mock.patch.object(fake_driver, 'execute')
    def test_container_execute(self, mock_execute):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_exec(
            self.context, container, 'fake_cmd')
        mock_execute.assert_called_once_with(container, 'fake_cmd')

    @mock.patch.object(fake_driver, 'execute')
    def test_container_execute_failed(self, mock_execute):
        container = Container(self.context, **utils.get_test_container())
        mock_execute.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_exec,
                          self.context, container, 'fake_cmd')

    @mock.patch.object(fake_driver, 'kill')
    def test_container_kill(self, mock_kill):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._do_container_kill(self.context, container, None)
        mock_kill.assert_called_once_with(container, None)

    @mock.patch.object(fake_driver, 'kill')
    def test_container_kill_failed(self, mock_kill):
        container = Container(self.context, **utils.get_test_container())
        mock_kill.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager._do_container_kill,
                          self.context, container, None, reraise=True)

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'update')
    def test_container_update(self, mock_update, mock_save):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_update(self.context, container,
                                              {'memory': 512})
        mock_save.assert_called_with(self.context)
        mock_update.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'update')
    def test_container_update_failed(self, mock_update):
        container = Container(self.context, **utils.get_test_container())
        mock_update.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_update,
                          self.context, container, {})

    @mock.patch.object(fake_driver, 'attach')
    @mock.patch('zun.container.driver.ContainerDriver.get_websocket_url')
    def test_container_attach(self, mock_attach, mock_getwebsocket_url):
        container = Container(self.context, **utils.get_test_container())
        mock_getwebsocket_url.return_value = "ws://test"
        self.compute_manager.container_attach(self.context, container)
        mock_attach.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'attach')
    def test_container_attach_failed(self, mock_attach):
        container = Container(self.context, **utils.get_test_container())
        mock_attach.side_effect = Exception
        self.assertRaises(exception.ZunException,
                          self.compute_manager.container_attach,
                          self.context, container)

    @mock.patch.object(fake_driver, 'resize')
    def test_container_resize(self, mock_resize):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_resize(self.context,
                                              container, "100", "100")
        mock_resize.assert_called_once_with(container, "100", "100")

    @mock.patch.object(fake_driver, 'resize')
    def test_container_resize_failed(self, mock_resize):
        container = Container(self.context, **utils.get_test_container())
        mock_resize.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_resize,
                          self.context, container, "100", "100")
