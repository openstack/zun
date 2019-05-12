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
            LOG.error("Container driver option required, "
                      "but not specified")
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
    """Base class for container drivers."""

    def create(self, context, container, **kwargs):
        """Create a container."""
        raise NotImplementedError()

    def commit(self, context, container, repository, tag):
        """Commit a container."""
        raise NotImplementedError()

    def delete(self, context, container, force):
        """Delete a container."""
        raise NotImplementedError()

    def list(self, context):
        """List all containers."""
        raise NotImplementedError()

    def update_containers_states(self, context, containers, manager):
        """Update containers states."""
        raise NotImplementedError()

    def show(self, context, container):
        """Show the details of a container."""
        raise NotImplementedError()

    def reboot(self, context, container):
        """Reboot a container."""
        raise NotImplementedError()

    def stop(self, context, container):
        """Stop a container."""
        raise NotImplementedError()

    def start(self, context, container):
        """Start a container."""
        raise NotImplementedError()

    def pause(self, context, container):
        """Pause a container."""
        raise NotImplementedError()

    def unpause(self, context, container):
        """Unpause a container."""
        raise NotImplementedError()

    def show_logs(self, context, container, stdout=True, stderr=True,
                  timestamps=False, tail='all', since=None):
        """Show logs of a container."""
        raise NotImplementedError()

    def execute_create(self, context, container, command, **kwargs):
        """Create an execute instance for running a command."""
        raise NotImplementedError()

    def execute_run(self, exec_id):
        """Run the command specified by an execute instance."""
        raise NotImplementedError()

    def execute_resize(self, exec_id, height, width):
        """Resizes the tty session used by the exec."""
        raise NotImplementedError()

    def kill(self, context, container, signal):
        """Kill a container with specified signal."""
        raise NotImplementedError()

    def get_websocket_url(self, context, container):
        """Get websocket url of a container."""
        raise NotImplementedError()

    def resize(self, context, container, height, weight):
        """Resize tty of a container."""
        raise NotImplementedError()

    def top(self, context, container, ps_args):
        """Display the running processes inside the container."""
        raise NotImplementedError()

    def get_archive(self, context, container, path):
        """Copy resource from a container."""
        raise NotImplementedError()

    def put_archive(self, context, container, path, data):
        """Copy resource to a container."""
        raise NotImplementedError()

    def stats(self, context, container):
        """Display stats of the container."""
        raise NotImplementedError()

    def get_container_name(self, container):
        """Retrieve container name."""
        raise NotImplementedError()

    def get_addresses(self, context, container):
        """Retrieve IP addresses of the container."""

    def update(self, context, container):
        """Update a container."""
        raise NotImplementedError()

    def get_host_numa_topology(self):
        numa_topo_obj = objects.NUMATopology()
        os_capability_linux.LinuxHost().get_host_numa_topology(numa_topo_obj)
        return numa_topo_obj

    def get_pci_resources(self):
        return os_capability_linux.LinuxHost().get_pci_resources()

    def get_host_mem(self):
        return os_capability_linux.LinuxHost().get_host_mem()

    def get_host_info(self):
        raise NotImplementedError()

    def get_total_disk_for_container(self):
        return NotImplementedError()

    def attach_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def detach_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def delete_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def is_volume_available(self, context, volume_mapping):
        raise NotImplementedError()

    def is_volume_deleted(self, context, volume_mapping):
        raise NotImplementedError()

    def add_security_group(self, context, container, security_group, **kwargs):
        raise NotImplementedError()

    def remove_security_group(self, context, container, security_group,
                              **kwargs):
        raise NotImplementedError()

    def get_available_nodes(self):
        pass

    def get_available_resources(self):
        """Retrieve resource information.

        This method is called when nova-compute launches, and
        as part of a periodic task that records the results in the DB.

        :returns: dictionary containing resource info
        """
        data = {}

        numa_topo_obj = self.get_host_numa_topology()
        data['numa_topology'] = numa_topo_obj
        meminfo = self.get_host_mem()
        (mem_total, mem_free, mem_ava, mem_used) = meminfo
        data['mem_total'] = mem_total // units.Ki
        data['mem_free'] = mem_free // units.Ki
        data['mem_available'] = mem_ava // units.Ki
        data['mem_used'] = mem_used // units.Ki
        info = self.get_host_info()
        data['total_containers'] = info['total_containers']
        data['running_containers'] = info['running_containers']
        data['paused_containers'] = info['paused_containers']
        data['stopped_containers'] = info['stopped_containers']
        data['cpus'] = info['cpus']
        data['architecture'] = info['architecture']
        data['os_type'] = info['os_type']
        data['os'] = info['os']
        data['kernel_version'] = info['kernel_version']
        data['labels'] = info['labels']
        disk_total = self.get_total_disk_for_container()
        data['disk_total'] = disk_total
        disk_quota_supported = self.node_support_disk_quota()
        data['disk_quota_supported'] = disk_quota_supported
        data['runtimes'] = info['runtimes']
        data['enable_cpu_pinning'] = info['enable_cpu_pinning']

        return data

    def node_is_available(self, nodename):
        """Return whether this compute service manages a particular node."""
        if nodename in self.get_available_nodes():
            return True
        return False

    def network_detach(self, context, container, network):
        raise NotImplementedError()

    def network_attach(self, context, container, requested_network):
        raise NotImplementedError()

    def create_network(self, context, network):
        raise NotImplementedError()

    def delete_network(self, context, network):
        raise NotImplementedError()

    def inspect_network(self, network):
        raise NotImplementedError()

    def node_support_disk_quota(self):
        raise NotImplementedError()

    def get_host_default_base_size(self):
        raise NotImplementedError()

    def pull_image(self, context, repo, tag, **kwargs):
        raise NotImplementedError()

    def search_image(self, context, repo, tag, driver_name, exact_match):
        raise NotImplementedError()

    def create_image(self, context, image_name, image_driver):
        raise NotImplementedError()

    def upload_image_data(self, context, image, image_tag, image_data,
                          image_driver):
        raise NotImplementedError()

    def delete_committed_image(self, context, img_id, image_driver):
        raise NotImplementedError()

    def delete_image(self, context, img_id, image_driver):
        raise NotImplementedError()

    def create_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()

    def delete_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()
