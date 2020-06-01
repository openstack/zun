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

from unittest import mock

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zun.common import exception
from zun.common import utils
import zun.conf
from zun.tests import base
from zun.volume import driver


CONF = zun.conf.CONF


class CinderVolumeDriverTestCase(base.TestCase):

    def setUp(self):
        super(CinderVolumeDriverTestCase, self).setUp()
        self.fake_uuid = uuidutils.generate_uuid()
        self.fake_volume_id = 'fake-volume-id'
        self.fake_devpath = '/fake-path'
        self.fake_mountpoint = '/fake-mountpoint'
        self.fake_container_path = '/fake-container-path'
        self.fake_conn_info = {
            'data': {'device_path': self.fake_devpath},
        }
        self.volmap = mock.MagicMock()
        self.volmap.volume.uuid = self.fake_uuid
        self.volmap.volume_provider = 'cinder'
        self.volmap.volume_id = self.fake_volume_id
        self.volmap.container_path = self.fake_container_path
        self.volmap.connection_info = jsonutils.dumps(self.fake_conn_info)

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
        self.volmap.connection_info = None
        volume_driver.attach(self.context, self.volmap)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volmap)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
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
        self.volmap.volume_provider = 'unknown'
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volmap)

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
        self.volmap.connection_info = None
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volmap)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volmap)
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
        self.volmap.connection_info = None
        self.assertRaises(exception.ZunException,
                          volume_driver.attach, self.context, self.volmap)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volmap)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
        mock_do_mount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint, CONF.volume.fstype)
        mock_cinder_workflow.detach_volume.assert_called_once_with(
            self.context, self.volmap)

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
        self.volmap.connection_info = None
        self.assertRaises(TestException1,
                          volume_driver.attach, self.context, self.volmap)

        mock_cinder_workflow.attach_volume.assert_called_once_with(self.volmap)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
        mock_do_mount.assert_called_once_with(
            self.fake_devpath, self.fake_mountpoint, CONF.volume.fstype)
        mock_cinder_workflow.detach_volume.assert_called_once_with(
            self.context, self.volmap)

    @mock.patch('shutil.rmtree')
    @mock.patch('zun.common.mount.do_unmount')
    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_detach(self, mock_cinder_workflow_cls, mock_get_mountpoint,
                    mock_do_unmount, mock_rmtree):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        volume_driver.detach(self.context, self.volmap)
        mock_cinder_workflow.detach_volume.\
            assert_called_once_with(self.context, self.volmap)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
        mock_do_unmount.assert_called_once_with(self.fake_mountpoint)
        mock_rmtree.assert_called_once_with(self.fake_mountpoint)

    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_bind_mount(self, mock_cinder_workflow_cls, mock_get_mountpoint):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        source, destination = volume_driver.bind_mount(
            self.context, self.volmap)

        self.assertEqual(self.fake_mountpoint, source)
        self.assertEqual(self.fake_container_path, destination)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)

    @mock.patch('zun.common.mount.get_mountpoint')
    @mock.patch('zun.common.mount.Mounter.read_mounts')
    @mock.patch('zun.volume.cinder_workflow.CinderWorkflow')
    def test_delete(self, mock_cinder_workflow_cls, mock_read_mounts,
                    mock_get_mountpoint):
        mock_cinder_workflow = mock.MagicMock()
        mock_cinder_workflow_cls.return_value = mock_cinder_workflow
        mock_cinder_workflow.delete_volume.return_value = self.fake_volume_id
        mock_get_mountpoint.return_value = self.fake_mountpoint

        volume_driver = driver.Cinder()
        volume_driver.delete(self.context, self.volmap)

        mock_cinder_workflow.delete_volume.assert_called_once_with(self.volmap)


class LocalVolumeDriverTestCase(base.TestCase):

    def setUp(self):
        super(LocalVolumeDriverTestCase, self).setUp()
        self.fake_uuid = uuidutils.generate_uuid()
        self.fake_mountpoint = '/fake-mountpoint'
        self.fake_container_path = '/fake-container-path'
        self.fake_contents = 'fake-contents'
        self.volmap = mock.MagicMock()
        self.volmap.volume.uuid = self.fake_uuid
        self.volmap.volume_provider = 'local'
        self.volmap.container_path = self.fake_container_path
        self.volmap.contents = self.fake_contents

    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('zun.common.mount.get_mountpoint')
    def test_attach(self, mock_get_mountpoint, mock_ensure_tree):
        mock_get_mountpoint.return_value = self.fake_mountpoint
        volume_driver = driver.Local()

        with mock.patch('zun.volume.driver.open', mock.mock_open()
                        ) as mock_open:
            volume_driver.attach(self.context, self.volmap)

        expected_file_path = self.fake_mountpoint + '/' + self.fake_uuid
        mock_open.assert_called_once_with(expected_file_path, 'wb')
        mock_open().write.assert_called_once_with(
            utils.decode_file_data(self.fake_contents))
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)

    @mock.patch('shutil.rmtree')
    @mock.patch('zun.common.mount.get_mountpoint')
    def test_detach(self, mock_get_mountpoint, mock_rmtree):
        mock_get_mountpoint.return_value = self.fake_mountpoint
        volume_driver = driver.Local()
        volume_driver.detach(self.context, self.volmap)

        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
        mock_rmtree.assert_called_once_with(self.fake_mountpoint)

    @mock.patch('zun.common.mount.get_mountpoint')
    def test_bind_mount(self, mock_get_mountpoint):
        mock_get_mountpoint.return_value = self.fake_mountpoint
        volume_driver = driver.Local()
        source, destination = volume_driver.bind_mount(
            self.context, self.volmap)

        expected_file_path = self.fake_mountpoint + '/' + self.fake_uuid
        self.assertEqual(expected_file_path, source)
        self.assertEqual(self.fake_container_path, destination)
        mock_get_mountpoint.assert_called_once_with(self.fake_uuid)
