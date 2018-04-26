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

from oslo_serialization import jsonutils

from zun.common import exception
import zun.conf
from zun.tests import base
from zun.volume import driver


CONF = zun.conf.CONF


class VolumeDriverTestCase(base.TestCase):

    def setUp(self):
        super(VolumeDriverTestCase, self).setUp()
        self.fake_volume_id = 'fake-volume-id'
        self.fake_devpath = '/fake-path'
        self.fake_mountpoint = '/fake-mountpoint'
        self.fake_container_path = '/fake-container-path'
        self.fake_conn_info = {
            'data': {'device_path': self.fake_devpath},
        }
        self.volume = mock.MagicMock()
        self.volume.volume_provider = 'cinder'
        self.volume.volume_id = self.fake_volume_id
        self.volume.container_path = self.fake_container_path
        self.volume.connection_info = jsonutils.dumps(self.fake_conn_info)

    @mock.patch('zun.common.mount.do_mount')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_attach(self, mock_cinder_workflow_cls, mock_get_mountpoint,
                    mock_ensure_tree, mock_do_mount):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.attach_volume.return_value = self.fake_devpath
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        volume_driver.attach(self.context, self.volume)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volume)
        mock_get_mountpoint.assert_called_once_with(self.fake_volume_id)
        mock_do_mount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint, CONF.volume.fstype)
        mock_cinder_workflow.detach_volume.assert_not_called()

    @mock.patch('zun.common.mount.do_mount')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_attach_unknown_provider(self, mock_cinder_workflow_cls,
                                     mock_get_mountpoint, mock_ensure_tree,
                                     mock_do_mount):
        volume_driver = driver.Cinder()
        self.volume.volume_provider = 'unknown'
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volume)

    @mock.patch('zun.common.mount.do_mount')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_attach_fail_attach(self, mock_cinder_workflow_cls,
                                mock_get_mountpoint, mock_ensure_tree,
                                mock_do_mount):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.attach_volume.side_effect = \
            exception.ZunException()
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volume)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volume)
        mock_get_mountpoint.assert_not_called()
        mock_do_mount.assert_not_called()
        mock_cinder_workflow.detach_volume.assert_not_called()

    @mock.patch('zun.common.mount.do_mount')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_attach_fail_mount(self, mock_cinder_workflow_cls,
                               mock_get_mountpoint, mock_ensure_tree,
                               mock_do_mount):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.attach_volume.return_value = self.fake_devpath
        mock_get_mountpoint.return_value = self.fake_mountpoint
        mock_do_mount.side_effect = exception.ZunException()

        volume_driver = driver.Cinder()
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volume)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volume)
        mock_get_mountpoint.assert_called_once_with(self.fake_volume_id)
        mock_do_mount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint, CONF.volume.fstype)
        mock_cinder_workflow.detach_volume.assert_called_once_with(self.volume)

    @mock.patch('zun.common.mount.do_mount')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_attach_fail_mount_and_detach(self, mock_cinder_workflow_cls,
                                          mock_get_mountpoint,
                                          mock_ensure_tree,
                                          mock_do_mount):
        class TestException1(Exception):
            pass

        class TestException2(Exception):
            pass

        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.attach_volume.return_value = self.fake_devpath
        mock_get_mountpoint.return_value = self.fake_mountpoint
        mock_do_mount.side_effect = TestException1()
        mock_cinder_workflow.detach_volume.side_effect = TestException2()

        volume_driver = driver.Cinder()
        self.assertRaises(TestException1,
                          volume_driver.attach, self.context, self.volume)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volume)
        mock_get_mountpoint.assert_called_once_with(self.fake_volume_id)
        mock_do_mount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint, CONF.volume.fstype)
        mock_cinder_workflow.detach_volume.assert_called_once_with(self.volume)

    @mock.patch('zun.common.mount.do_unmount')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_detach(self, mock_cinder_workflow_cls, mock_get_mountpoint,
                    mock_do_unmount):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.detach_volume.return_value = self.fake_devpath
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        volume_driver.detach(self.context, self.volume)

        mock_cinder_workflow.detach_volume.assert_called_once_with(self.volume)
        mock_get_mountpoint.assert_called_once_with(self.fake_volume_id)
        mock_do_unmount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint)

    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_bind_mount(self, mock_cinder_workflow_cls, mock_get_mountpoint):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        source, destination = volume_driver.bind_mount(
            self.context, self.volume)

        self.assertEqual(self.fake_mountpoint, source)
        self.assertEqual(self.fake_container_path, destination)
        mock_get_mountpoint.assert_called_once_with(self.fake_volume_id)

    @mock.patch('zun.common.mount.Mounter.read_mounts')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_delete(self, mock_cinder_workflow_cls, mock_read_mounts):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.delete_volume.return_value = self.fake_volume_id

        volume_driver = driver.Cinder()
        volume_driver.delete(self.context, self.volume)

        mock_cinder_workflow.delete_volume.assert_called_once_with(self.volume)
