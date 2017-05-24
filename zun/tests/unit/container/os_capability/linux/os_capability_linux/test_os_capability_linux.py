# Copyright 2017 IBM Corp.
#
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
import six

from mock import mock_open

from oslo_concurrency import processutils
from zun.common import exception
from zun.container.os_capability.linux import os_capability_linux
from zun.tests import base

LSCPU_ON = """# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# Socket,CPU,Online
0,0,Y
0,8,Y
1,16,Y
1,24,Y
2,32,Y"""

LSCPU_NO_ONLINE = """# The following is the parsable format, which can be fed to
# programs. Each different item in every column has an unique ID
# starting from zero.
# Socket,CPU
0,0
0,1
1,2
1,3"""


class TestOSCapability(base.BaseTestCase):
    @mock.patch('oslo_concurrency.processutils.execute')
    def test_get_cpu_numa_info_with_online(self, mock_output):
        mock_output.return_value = LSCPU_ON
        output = os_capability_linux.LinuxHost().get_cpu_numa_info()
        expected_output = {'0': [0, 8], '1': [16, 24], '2': [32]}
        self.assertEqual(expected_output, output)

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_get_cpu_numa_info_exception(self, mock_output):
        mock_output.side_effect = processutils.ProcessExecutionError()
        self.assertRaises(exception.CommandError,
                          os_capability_linux.LinuxHost().get_cpu_numa_info)

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_get_cpu_numa_info_without_online(self, mock_output):
        mock_output.side_effect = [processutils.ProcessExecutionError(),
                                   LSCPU_NO_ONLINE]
        expected_output = {'0': [0, 1], '1': [2, 3]}
        output = os_capability_linux.LinuxHost().get_cpu_numa_info()
        self.assertEqual(expected_output, output)

    def test_get_host_mem(self):
        data = ('MemTotal:        3882464 kB\nMemFree:         3514608 kB\n'
                'MemAvailable:    3556372 kB\n')
        m_open = mock_open(read_data=data)
        with mock.patch.object(six.moves.builtins, "open", m_open,
                               create=True):
            output = os_capability_linux.LinuxHost().get_host_mem()
            used = (3882464 - 3556372)
            self.assertEqual((3882464, 3514608, 3556372, used), output)
