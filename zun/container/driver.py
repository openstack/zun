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
from oslo_utils import units

from zun.common.i18n import _
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
            LOG.error(("Container driver option required, "
                       "but not specified"))
            sys.exit(1)

    LOG.info("Loading container driver '%s'", container_driver)
    try:
        if not container_driver.startswith('zun.'):
            container_driver = 'zun.container.%s' % container_driver
        driver = importutils.import_object(container_driver)
        if not isinstance(driver, ContainerDriver):
            raise Exception(_('Expected driver of type: %s') %
                            str(ContainerDriver))

        return driver
    except ImportError:
        LOG.exception("Unable to load the container driver")
        sys.exit(1)


class ContainerDriver(object):
    '''Base class for container drivers.'''

    def create(self, context, container, sandbox_name=None):
        """Create a container."""
        raise NotImplementedError()

    def commit(self, container, repository, tag):
        """commit a container."""
        raise NotImplementedError()

    def delete(self, container, force):
        """Delete a container."""
        raise NotImplementedError()

    def list(self, context):
        """List all containers."""
        raise NotImplementedError()

    def update_containers_states(self, context, containers):
        """Update containers states."""
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

    def execute_create(self, container, command, **kwargs):
        """Create an execute instance for running a command."""
        raise NotImplementedError()

    def execute_run(self, exec_id):
        """Run the command specified by an execute instance."""
        raise NotImplementedError()

    def execute_resize(self, exec_id, height, width):
        """Resizes the tty session used by the exec."""
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

    def stats(self, container):
        """Display stats of the container(s)."""
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

    def get_host_numa_topology(self):
        numa_topo_obj = objects.NUMATopology()
        os_capability_linux.LinuxHost().get_host_numa_topology(numa_topo_obj)
        return numa_topo_obj

    def get_host_mem(self):
        return os_capability_linux.LinuxHost().get_host_mem()

    def get_host_info(self):
        raise NotImplementedError()

    def get_cpu_used(self):
        raise NotImplementedError()

    def add_security_group(self, context, sandbox_id, security_group):
        raise NotImplementedError()

    def get_available_resources(self, node):
        numa_topo_obj = self.get_host_numa_topology()
        node.numa_topology = numa_topo_obj
        meminfo = self.get_host_mem()
        (mem_total, mem_free, mem_ava, mem_used) = meminfo
        node.mem_total = mem_total // units.Ki
        node.mem_free = mem_free // units.Ki
        node.mem_available = mem_ava // units.Ki
        node.mem_used = mem_used // units.Ki
        info = self.get_host_info()
        (total, running, paused, stopped, cpus,
         architecture, os_type, os, kernel_version, labels) = info
        node.total_containers = total
        node.running_containers = running
        node.paused_containers = paused
        node.stopped_containers = stopped
        node.cpus = cpus
        node.architecture = architecture
        node.os_type = os_type
        node.os = os
        node.kernel_version = kernel_version
        cpu_used = self.get_cpu_used()
        node.cpu_used = cpu_used
        node.labels = labels

    def node_is_available(self, nodename):
        """Return whether this compute service manages a particular node."""
        if nodename in self.get_available_nodes():
            return True
        return False
