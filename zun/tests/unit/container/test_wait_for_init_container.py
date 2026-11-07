#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#    implied. See the License for the specific language governing
#    permissions and limitations under the License.

"""A capsule waits for its init containers with the tenacity installed.

Both drivers waited with Retrying.call(), which tenacity removed in 8.0:
every capsule with an init container failed to create with "'Retrying'
object has no attribute 'call'". These run the real tenacity rather than
a mock of it, so a later change in its API shows up as a failing test.
"""

from unittest import mock

from zun.common import consts
from zun.common import exception
from zun.container.cri import driver as cri_driver
from zun.container.docker import driver as docker_driver
from zun.tests import base


class WaitForInitContainerTest(base.TestCase):

    def _wait(self, drv, show, statuses):
        answers = iter(statuses)
        calls = []

        def answer(*args):
            calls.append(args)
            return mock.Mock(status=next(answers))

        with mock.patch.object(drv, show, side_effect=answer), \
                mock.patch('time.sleep'):
            drv._wait_for_init_container({}, mock.Mock(), timeout=30)
        return len(calls)

    def test_cri_waits_until_it_stops(self):
        drv = cri_driver.CriDriver.__new__(cri_driver.CriDriver)
        self.assertEqual(3, self._wait(
            drv, '_show_container',
            [consts.RUNNING, consts.RUNNING, consts.STOPPED]))

    def test_docker_waits_until_it_stops(self):
        drv = docker_driver.DockerDriver.__new__(docker_driver.DockerDriver)
        self.assertEqual(2, self._wait(
            drv, 'show', [consts.RUNNING, consts.STOPPED]))

    def test_an_unexpected_status_is_raised_not_retried(self):
        drv = docker_driver.DockerDriver.__new__(docker_driver.DockerDriver)
        self.assertRaises(exception.ZunException, self._wait,
                          drv, 'show', [consts.ERROR])
