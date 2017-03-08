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

import sys

from oslo_log import log as logging
from oslo_utils import importutils

from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common.i18n import _LI
import zun.conf
from zun.container.os_capability.linux import os_capability_linux
from zun import objects

LOG = logging.getLogger(__name__)
CONF = zun.conf.CONF


def load_container_driver(container_driver=None):
    """Load a container driver module.

    Load the container driver module specified by the container_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.
    :param container_driver: a container driver name to override the config opt
    :returns: a ContainerDriver instance
    """
    if not container_driver:
        container_driver = CONF.container_driver
        if not container_driver:
            LOG.error(_LE("Container driver option required, "
                          "but not specified"))
            sys.exit(1)

    LOG.info(_LI("Loading container driver '%s'"), container_driver)
    try:
        if not container_driver.startswith('zun.'):
            container_driver = 'zun.container.%s' % container_driver
        driver = importutils.import_object(container_driver)
        if not isinstance(driver, ContainerDriver):
            raise Exception(_('Expected driver of type: %s') %
                            str(ContainerDriver))

        return driver
    except ImportError:
        LOG.exception(_LE("Unable to load the container driver"))
        sys.exit(1)


class ContainerDriver(object):
    '''Base class for container drivers.'''

    def create(self, context, container, sandbox_name=None):
        """Create a container."""
        raise NotImplementedError()

    def delete(self, container, force):
        """Delete a container."""
        raise NotImplementedError()

    def list(self):
        """List all containers."""
        raise NotImplementedError()

    def show(self, container):
        """Show the details of a container."""
        raise NotImplementedError()

    def reboot(self, container):
        """Reboot a container."""
        raise NotImplementedError()

    def stop(self, container):
        """Stop a container."""
        raise NotImplementedError()

    def start(self, container):
        """Start a container."""
        raise NotImplementedError()

    def pause(self, container):
        """Pause a container."""
        raise NotImplementedError()

    def unpause(self, container):
        """Pause a container."""
        raise NotImplementedError()

    def show_logs(self, container, stdout=True, stderr=True,
                  timestamps=False, tail='all', since=None):
        """Show logs of a container."""
        raise NotImplementedError()

    def execute(self, container, command):
        """Execute a command in a running container."""
        raise NotImplementedError()

    def kill(self, container, signal):
        """kill signal to a container."""
        raise NotImplementedError()

    def get_websocket_url(self, container):
        """get websocket url of a container."""
        raise NotImplementedError()

    def resize(self, container, height, weight):
        """resize tty of a container."""
        raise NotImplementedError()

    def top(self, container, ps_args):
        """display the running processes inside the container."""
        raise NotImplementedError()

    def get_archive(self, container, path):
        """copy resource froma container."""
        raise NotImplementedError()

    def put_archive(self, container, path, data):
        """copy resource to a container."""
        raise NotImplementedError()

    def create_sandbox(self, context, container, **kwargs):
        """Create a sandbox."""
        raise NotImplementedError()

    def delete_sandbox(self, context, sandbox_id):
        """Delete a sandbox."""
        raise NotImplementedError()

    # Note: This is not currently used, but
    # may be used later
    def stop_sandbox(self, context, sandbox_id):
        """Stop a sandbox."""
        raise NotImplementedError()

    def get_sandbox_id(self, container):
        """Retrieve sandbox ID."""
        raise NotImplementedError()

    def set_sandbox_id(self, container, sandbox_id):
        """Set sandbox ID."""
        raise NotImplementedError()

    def get_sandbox_name(self, container):
        """Retrieve sandbox name."""
        raise NotImplementedError()

    def get_container_name(self, container):
        """Retrieve sandbox name."""
        raise NotImplementedError()

    def get_addresses(self, context, container):
        """Retrieve IP addresses of the container."""

    def update(self, container):
        """Update a container."""
        raise NotImplementedError()

    def get_available_resources(self, compute_node_obj):
        numa_topo_obj = objects.NUMATopology()
        os_capability_linux.LinuxHost().get_host_numa_topology(numa_topo_obj)
        compute_node_obj.numa_topology = numa_topo_obj
