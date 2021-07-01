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

import copy
import sys

import os_resource_classes as orc
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import units
import psutil
from stevedore import driver as stevedore_driver

from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
import zun.conf
from zun.container.os_capability.linux import os_capability_linux
from zun import objects
from zun.volume import driver as vol_driver


LOG = logging.getLogger(__name__)
CONF = zun.conf.CONF


# TODO(hongbin): define a list of standard traits keyed by capabilities
CAPABILITY_TRAITS_MAP = {}


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
        if container_driver.startswith('docker.driver.'):
            # case 1: (deprecated) CONF.container_driver is
            # 'docker.driver.DockerDriver'
            container_driver = 'zun.container.%s' % container_driver
            driver = importutils.import_object(container_driver)
        elif container_driver.startswith('zun.'):
            # case 2: (deprecated) CONF.container_driver is
            # 'zun.container.docker.driver.DockerDriver'
            driver = importutils.import_object(container_driver)
        else:
            # case 3: CONF.container_driver is (for example) 'docker'
            # load from entry point in this case.
            driver = stevedore_driver.DriverManager(
                "zun.container.driver",
                container_driver,
                invoke_on_load=True).driver

        if not isinstance(driver, ContainerDriver):
            raise Exception(_('Expected driver of type: %s') %
                            str(ContainerDriver))

        return driver
    except ImportError:
        LOG.exception("Unable to load the container driver")
        sys.exit(1)


def load_capsule_driver():
    driver = stevedore_driver.DriverManager(
        "zun.capsule.driver",
        CONF.capsule_driver,
        invoke_on_load=True).driver

    if not isinstance(driver, CapsuleDriver):
        raise Exception(_('Expected driver of type: %s') %
                        str(ContainerDriver))

    return driver


class BaseDriver(object):
    """Base class for driver."""

    def __init__(self):
        self.volume_drivers = {}
        for driver_name in CONF.volume.driver_list:
            driver = vol_driver.driver(driver_name)
            self.volume_drivers[driver_name] = driver
        self.cpu_allocation_ratio = CONF.compute.cpu_allocation_ratio
        self.ram_allocation_ratio = CONF.compute.ram_allocation_ratio

    def get_host_numa_topology(self):
        numa_topo_obj = objects.NUMATopology()
        os_capability_linux.LinuxHost().get_host_numa_topology(numa_topo_obj)
        return numa_topo_obj

    def get_pci_resources(self):
        return os_capability_linux.LinuxHost().get_pci_resources()

    def get_host_mem(self):
        return os_capability_linux.LinuxHost().get_host_mem()

    def get_total_disk_for_container(self):
        disk_usage = psutil.disk_usage('/')
        total_disk = disk_usage.total / 1024 ** 3
        # TODO(hongbin): deprecate reserve_disk_for_image in flavor of
        # reserved_host_disk_mb
        return (int(total_disk),
                int(total_disk * CONF.compute.reserve_disk_for_image))

    def _get_volume_driver(self, volume_mapping):
        driver_name = volume_mapping.volume_provider
        driver = self.volume_drivers.get(driver_name)
        if not driver:
            msg = _("The volume provider '%s' is not supported") % driver_name
            raise exception.ZunException(msg)

        return driver

    def attach_volume(self, context, volume_mapping):
        volume_driver = self._get_volume_driver(volume_mapping)
        volume_driver.attach(context, volume_mapping)

    def detach_volume(self, context, volume_mapping):
        volume_driver = self._get_volume_driver(volume_mapping)
        volume_driver.detach(context, volume_mapping)

    def delete_volume(self, context, volume_mapping):
        volume_driver = self._get_volume_driver(volume_mapping)
        volume_driver.delete(context, volume_mapping)

    def is_volume_available(self, context, volume_mapping):
        volume_driver = self._get_volume_driver(volume_mapping)
        return volume_driver.is_volume_available(context, volume_mapping)

    def is_volume_deleted(self, context, volume_mapping):
        volume_driver = self._get_volume_driver(volume_mapping)
        return volume_driver.is_volume_deleted(context, volume_mapping)

    def get_available_nodes(self):
        return [CONF.host]

    def node_support_disk_quota(self):
        return False

    def get_host_default_base_size(self):
        return None

    def get_available_resources(self):
        """Retrieve resource information.

        This method is called when zun-compute launches, and
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
        disk_total, disk_reserved = self.get_total_disk_for_container()
        data['disk_total'] = disk_total - disk_reserved
        disk_quota_supported = self.node_support_disk_quota()
        data['disk_quota_supported'] = disk_quota_supported
        data['enable_cpu_pinning'] = CONF.compute.enable_cpu_pinning

        return data

    def node_is_available(self, nodename):
        """Return whether this compute service manages a particular node."""
        if nodename in self.get_available_nodes():
            return True
        return False

    def update_provider_tree(self, provider_tree, nodename):
        """Update a ProviderTree object with current resource provider,
        inventory information.
        :param zun.compute.provider_tree.ProviderTree provider_tree:
            A zun.compute.provider_tree.ProviderTree object representing all
            the providers in the tree associated with the compute node, and any
            sharing providers (those with the ``MISC_SHARES_VIA_AGGREGATE``
            trait) associated via aggregate with any of those providers (but
            not *their* tree- or aggregate-associated providers), as currently
            known by placement.
        :param nodename:
            String name of the compute node (i.e. ComputeNode.hostname)
            for which the caller is requesting updated provider information.
        """
        def _get_local_gb_info():
            return self.get_total_disk_for_container()[0]

        def _get_memory_mb_total():
            mem_total, mem_free, mem_ava, mem_used = self.get_host_mem()
            return mem_total // units.Ki

        def _get_vcpu_total():
            return psutil.cpu_count()

        disk_gb = _get_local_gb_info()
        memory_mb = _get_memory_mb_total()
        vcpus = _get_vcpu_total()

        # NOTE(yikun): If the inv record does not exists, the allocation_ratio
        # will use the CONF.xxx_allocation_ratio value if xxx_allocation_ratio
        # is set, and fallback to use the initial_xxx_allocation_ratio
        # otherwise.
        inv = provider_tree.data(nodename).inventory
        ratios = self._get_allocation_ratios(inv)
        self.cpu_allocation_ratio = ratios[orc.VCPU]
        self.ram_allocation_ratio = ratios[orc.MEMORY_MB]
        result = {
            orc.VCPU: {
                'total': vcpus,
                'min_unit': 1,
                'max_unit': vcpus,
                'step_size': 1,
                'allocation_ratio': ratios[orc.VCPU],
                # TODO(hongbin): handle the case that the zun's reserved value
                # override the nova's one
                'reserved': CONF.compute.reserved_host_cpus,
            },
            orc.MEMORY_MB: {
                'total': memory_mb,
                'min_unit': 1,
                'max_unit': memory_mb,
                'step_size': 1,
                'allocation_ratio': ratios[orc.MEMORY_MB],
                # TODO(hongbin): handle the case that the zun's reserved value
                # override the nova's one
                'reserved': CONF.compute.reserved_host_memory_mb,
            },
        }

        # If a sharing DISK_GB provider exists in the provider tree, then our
        # storage is shared, and we should not report the DISK_GB inventory in
        # the compute node provider.
        # TODO(efried): Reinstate non-reporting of shared resource by the
        # compute RP once the issues from bug #1784020 have been resolved.
        if provider_tree.has_sharing_provider(orc.DISK_GB):
            LOG.debug('Ignoring sharing provider - see bug #1784020')
        result[orc.DISK_GB] = {
            'total': disk_gb,
            'min_unit': 1,
            'max_unit': disk_gb,
            'step_size': 1,
            'allocation_ratio': ratios[orc.DISK_GB],
            # TODO(hongbin): handle the case that the zun's reserved value
            # override the nova's one
            'reserved': self._get_reserved_host_disk_gb_from_config(),
        }

        provider_tree.update_inventory(nodename, result)

        # Now that we updated the ProviderTree, we want to store it locally
        # so that spawn() or other methods can access it thru a getter
        self.provider_tree = copy.deepcopy(provider_tree)

    def get_cpu_allocation_ratio(self):
        return self.cpu_allocation_ratio

    def get_ram_allocation_ratio(self):
        return self.ram_allocation_ratio

    @staticmethod
    def _get_allocation_ratios(inventory):
        """Get the cpu/ram/disk allocation ratios for the given inventory.

        This utility method is used to get the inventory allocation ratio
        for VCPU, MEMORY_MB and DISK_GB resource classes based on the following
        precedence:

        * Use ``[DEFAULT]/*_allocation_ratio`` if set - this overrides
          everything including externally set allocation ratios on the
          inventory via the placement API
        * Use ``[DEFAULT]/initial_*_allocation_ratio`` if a value does not
          exist for a given resource class in the ``inventory`` dict
        * Use what is already in the ``inventory`` dict for the allocation
          ratio if the above conditions are false

        :param inventory: dict, keyed by resource class, of inventory
                          information.
        :returns: Return a dict, keyed by resource class, of allocation ratio
        """
        keys = {'cpu': orc.VCPU,
                'ram': orc.MEMORY_MB,
                'disk': orc.DISK_GB}
        result = {}
        for res, rc in keys.items():
            attr = '%s_allocation_ratio' % res
            conf_ratio = getattr(CONF.compute, attr)
            if conf_ratio:
                result[rc] = conf_ratio
            elif rc not in inventory:
                result[rc] = getattr(CONF.compute, 'initial_%s' % attr)
            else:
                result[rc] = inventory[rc]['allocation_ratio']
        return result

    @staticmethod
    def _get_reserved_host_disk_gb_from_config():
        return utils.convert_mb_to_ceil_gb(CONF.compute.reserved_host_disk_mb)

    def capabilities_as_traits(self):
        """Returns this driver's capabilities dict where the keys are traits

        Traits can only be standard compute capabilities traits from
        the os-traits library.

        :returns: dict, keyed by trait, of this driver's capabilities where the
            values are booleans indicating if the driver supports the trait

        """
        traits = {}
        for capability, supported in self.capabilities.items():
            if capability in CAPABILITY_TRAITS_MAP:
                traits[CAPABILITY_TRAITS_MAP[capability]] = supported

        return traits


class ContainerDriver(object):
    """Interface for container driver."""

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

    def update(self, context, container):
        """Update a container."""
        raise NotImplementedError()

    def add_security_group(self, context, container, security_group, **kwargs):
        raise NotImplementedError()

    def remove_security_group(self, context, container, security_group,
                              **kwargs):
        raise NotImplementedError()

    def network_detach(self, context, container, network):
        raise NotImplementedError()

    def network_attach(self, context, container, requested_network):
        raise NotImplementedError()

    def create_network(self, context, network):
        raise NotImplementedError()

    def delete_network(self, context, network):
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


class CapsuleDriver(object):
    """Interface for container driver."""

    def create_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()

    def delete_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()
