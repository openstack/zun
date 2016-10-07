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

from oslo_config import cfg

from zun.common import exception
from zun.compute import manager
from zun.objects.container import Container
from zun.objects import fields
from zun.tests import base
from zun.tests.unit.container.fake_driver import FakeDriver as fake_driver
from zun.tests.unit.db import utils


class TestManager(base.TestCase):

    def setUp(self):
        super(TestManager, self).setUp()
        cfg.CONF.set_override(
            'container_driver',
            'zun.tests.unit.container.fake_driver.FakeDriver')
        self.compute_manager = manager.Manager()

    @mock.patch.object(Container, 'save')
    def test_fail_container(self, mock_save):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager._fail_container(container)
        self.assertEqual(fields.ContainerStatus.ERROR, container.status)
        self.assertIsNone(container.task_state)

    def test_validate_container_state(self):
        container = Container(self.context, **utils.get_test_container())
        container.status = 'Stopped'
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager._validate_container_state,
                          container, 'stop')
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager._validate_container_state,
                          container, 'pause')
        container.status = 'Running'
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager._validate_container_state,
                          container, 'start')
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager._validate_container_state,
                          container, 'unpause')

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(fake_driver, 'create')
    def test_container_create(self, mock_create, mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.return_value = 'fake_path'
        self.compute_manager._do_container_create(self.context, container)
        mock_save.assert_called_with()
        mock_pull.assert_called_once_with(self.context, container.image)
        mock_create.assert_called_once_with(container, 'fake_path')

    @mock.patch.object(Container, 'save')
    @mock.patch('zun.image.driver.pull_image')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_pull_image_failed(self, mock_fail,
                                                mock_pull, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_pull.side_effect = exception.DockerError
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(container)

    @mock.patch.object(Container, 'save')
    @mock.patch.object(fake_driver, 'create')
    @mock.patch.object(manager.Manager, '_fail_container')
    def test_container_create_docker_create_failed(self, mock_fail,
                                                   mock_create, mock_save):
        container = Container(self.context, **utils.get_test_container())
        mock_create.side_effect = exception.DockerError
        self.compute_manager._do_container_create(self.context, container)
        mock_fail.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete(self, mock_delete, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_delete(self. context, container, False)
        mock_delete.assert_called_once_with(container, False)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_delete_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_delete,
                          self.context, container, False)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'delete')
    def test_container_delete_failed(self, mock_delete, mock_validate):
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

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot(self, mock_reboot, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_reboot(self.context, container)
        mock_reboot.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_reboot_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_reboot,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'reboot')
    def test_container_reboot_failed(self, mock_reboot, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_reboot.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_reboot,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop(self, mock_stop, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_stop(self.context, container)
        mock_stop.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_stop_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_stop,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'stop')
    def test_container_stop_failed(self, mock_stop, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_stop.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_stop,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'start')
    def test_container_start(self, mock_start, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_start(self.context, container)
        mock_start.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_start_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_start,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'start')
    def test_container_start_failed(self, mock_start, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_start.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_start,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause(self, mock_pause, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_pause(self.context, container)
        mock_pause.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_pause_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_pause,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'pause')
    def test_container_pause_failed(self, mock_pause, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_pause.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_pause,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause(self, mock_unpause, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_unpause(self.context, container)
        mock_unpause.assert_called_once_with(container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_unpause_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_unpause,
                          self.context, container)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'unpause')
    def test_container_unpause_failed(self, mock_unpause, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_unpause.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_unpause,
                          self.context, container)

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        self.compute_manager.container_logs(self.context, container)
        mock_logs.assert_called_once_with(container)

    @mock.patch.object(fake_driver, 'show_logs')
    def test_container_logs_failed(self, mock_logs):
        container = Container(self.context, **utils.get_test_container())
        mock_logs.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_logs,
                          self.context, container)

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
        self.compute_manager.container_kill(self.context, container, None)
        mock_kill.assert_called_once_with(container, None)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    def test_container_kill_invalid_state(self, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_validate.side_effect = exception.InvalidStateException
        self.assertRaises(exception.InvalidStateException,
                          self.compute_manager.container_kill,
                          self.context, container, None)

    @mock.patch.object(manager.Manager, '_validate_container_state')
    @mock.patch.object(fake_driver, 'kill')
    def test_container_kill_failed(self, mock_kill, mock_validate):
        container = Container(self.context, **utils.get_test_container())
        mock_kill.side_effect = exception.DockerError
        self.assertRaises(exception.DockerError,
                          self.compute_manager.container_kill,
                          self.context, container, None)
