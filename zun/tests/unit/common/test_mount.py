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

import mock

from zun.common import exception
from zun.common import mount
from zun.tests import base


class TestMounter(base.BaseTestCase):
    def setUp(self):
        super(TestMounter, self).setUp()
        self.mountinfo = "/dev/0 /path/to/0 type0 flags 0 0\n" \
                         "/dev/1 /path/to/1 type1 flags 0 0\n" \
                         "/dev/2 /path/to/2 type2 flags,1,2=3 0 0\n"
        self.mounts = [
            mount.MountInfo(device='/dev/0', mountpoint='/path/to/0',
                            fstype='type0', opts='flags'),
            mount.MountInfo(device='/dev/1', mountpoint='/path/to/1',
                            fstype='type1', opts='flags'),
            mount.MountInfo(device='/dev/2', mountpoint='/path/to/2',
                            fstype='type2', opts='flags,1,2=3'),
        ]

    @mock.patch('zun.common.utils.execute')
    def test_mount(self, mock_execute):
        fake_devpath = '/dev/3'
        fake_mp = '/path/to/3'
        fake_fstype = 'ext4'
        mounter = mount.Mounter()
        mounter.mount(fake_devpath, fake_mp, fake_fstype)
        mock_execute.assert_called_once_with(
            'mount', '-t', fake_fstype, fake_devpath, fake_mp,
            run_as_root=True)

    @mock.patch('zun.common.utils.execute')
    def test_unmount_error(self, mock_execute):
        fake_devpath = '/dev/3'
        fake_mp = '/path/to/3'
        fake_fstype = 'ext4'
        mock_execute.side_effect = exception.CommandError()
        mounter = mount.Mounter()
        self.assertRaises(exception.MountException,
                          mounter.mount, fake_devpath, fake_mp, fake_fstype)

    @mock.patch('zun.common.utils.execute')
    def test_read_mounts(self, mock_execute):
        mock_execute.return_value = (self.mountinfo, '')
        expected_mounts = [str(m) for m in self.mounts]
        mounter = mount.Mounter()
        mounts = [str(m) for m in mounter.read_mounts()]
        self.assertEqual(len(expected_mounts), len(mounts))
        for m in mounts:
            self.assertIn(m, expected_mounts)

    @mock.patch('zun.common.utils.execute')
    def test_read_mounts_error(self, mock_execute):
        mock_execute.side_effect = exception.CommandError()
        mounter = mount.Mounter()
        self.assertRaises(exception.FileNotFound, mounter.read_mounts)

    @mock.patch('zun.common.utils.execute')
    @mock.patch('zun.common.mount.Mounter.read_mounts')
    def test_get_mps_by_device(self, mock_read_mounts, mock_execute):
        mock_execute.return_value = (self.mountinfo, '')
        mock_read_mounts.return_value = self.mounts
        mounter = mount.Mounter()
        self.assertEqual(['/path/to/0'],
                         mounter.get_mps_by_device('/dev/0'))
