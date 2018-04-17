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

from zun.common import consts
from zun.common import exception
from zun.common import utils
import zun.conf
from zun.container.docker import utils as docker_utils

CONF = zun.conf.CONF
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

    def get_storage_info(self):
        with docker_utils.docker_client() as docker:
            info = docker.info()
            storage_driver = str(info['Driver'])
            # DriverStatus is list. Convert it to dict
            driver_status = dict(info['DriverStatus'])
            backing_filesystem = \
                str(driver_status.get('Backing Filesystem'))
            default_base_size = driver_status.get('Base Device Size')
            if default_base_size:
                default_base_size = float(default_base_size.strip('GB'))
        return {
            'storage_driver': storage_driver,
            'backing_filesystem': backing_filesystem,
            'default_base_size': default_base_size
        }

    def check_supported_disk_quota(self):
        """Check your system be supported disk quota or not"""
        storage_info = self.get_storage_info()
        sp_disk_quota = True
        storage_driver = storage_info['storage_driver']
        backing_filesystem = storage_info['backing_filesystem']
        if storage_driver not in consts.SUPPORTED_STORAGE_DRIVERS:
            sp_disk_quota = False
        else:
            if storage_driver == 'overlay2':
                if backing_filesystem == 'xfs':
                    # Check project quota mount option
                    try:
                        cmd = "mount |grep $(df " + CONF.docker.docker_data_root + \
                              " |awk 'FNR==2 {print $1}') | grep 'xfs'" \
                              " |grep -E 'pquota|prjquota'"
                        utils.execute(cmd, shell=True)
                    except exception.CommandError:
                        sp_disk_quota = False
                else:
                    sp_disk_quota = False
        return sp_disk_quota
