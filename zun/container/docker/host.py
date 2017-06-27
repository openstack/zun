# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Manages information about the host.
"""

from oslo_log import log as logging

from zun.container.docker import utils as docker_utils

LOG = logging.getLogger(__name__)


class Host(object):

    def __init__(self):
        self._hostname = None

    def get_hostname(self):
        """Returns the hostname of the host."""
        with docker_utils.docker_client() as docker:
            hostname = docker.info()['Name']
            if self._hostname is None:
                self._hostname = hostname
            elif hostname != self._hostname:
                self._hostname = hostname
                LOG.warning('Hostname has changed from %(old)s '
                            'to %(new)s. A restart is required '
                            'to take effect.',
                            {'old': self._hostname, 'new': hostname})
        return self._hostname
