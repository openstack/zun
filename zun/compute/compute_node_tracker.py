# All Rights Reserved.
#
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

import collections
import copy
import socket

from oslo_log import log as logging
import retrying

from zun.common import consts
from zun.common import exception
from zun.common import utils
from zun.compute import claims
import zun.conf
from zun import objects
from zun.objects import base as obj_base
from zun.pci import manager as pci_manager
from zun.scheduler.client import query as scheduler_client


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
COMPUTE_RESOURCE_SEMAPHORE = "compute_resources"


class ComputeNodeTracker(object):
    def __init__(self, host, container_driver, capsule_driver, reportclient):
        self.host = host
        self.container_driver = container_driver
        self.capsule_driver = capsule_driver
        self.compute_node = None
        self.tracked_containers = {}
        self.old_resources = collections.defaultdict(objects.ComputeNode)
        self.scheduler_client = scheduler_client.SchedulerClient()
        self.pci_tracker = None
        self.reportclient = reportclient
        self.rp_uuid = None

    def _setup_pci_tracker(self, context, compute_node):
        if not self.pci_tracker:
            n_id = compute_node.uuid
            self.pci_tracker = pci_manager.PciDevTracker(context, node_id=n_id)
            dev_json = self.container_driver.get_pci_resources()
            self.pci_tracker.update_devices_from_compute_resources(dev_json)

            dev_pools_obj = self.pci_tracker.stats.to_device_pools_obj()
            compute_node.pci_device_pools = dev_pools_obj

    def update_available_resources(self, context):
        # TODO(hongbin): get available resources from capsule_driver
        # and aggregates resources
        resources = self.container_driver.get_available_resources()
        # We allow 'cpu_used' to be missing from the container driver,
        # but the DB requires it to be non-null so just initialize it to 0.
        resources.setdefault('cpu_used', 0)

        # Check if the compute_node is already registered
        node = self._get_compute_node(context)
        if not node:
            # If not, register it and pass the object to the driver
            node = objects.ComputeNode(context)
            node.hostname = self.host
            self._copy_resources(node, resources)
            node.create(context)
            LOG.info('Node created for :%(host)s', {'host': self.host})
        else:
            self._copy_resources(node, resources)
        node.rp_uuid = self._get_node_rp_uuid(context, node)
        self._setup_pci_tracker(context, node)
        self.compute_node = node
        self._update_available_resource(context)
        # NOTE(sbiswas7): Consider removing the return statement if not needed
        return node

    def _copy_resources(self, node, resources):
        keys = ["numa_topology", "mem_total", "mem_free", "mem_available",
                "mem_used", "total_containers", "running_containers",
                "paused_containers", "stopped_containers", "cpus",
                "architecture", "os_type", "os", "kernel_version", "cpu_used",
                "labels", "disk_total", "disk_quota_supported", "runtimes",
                "enable_cpu_pinning"]
        for key in keys:
            if key in resources:
                setattr(node, key, resources[key])

    def _get_compute_node(self, context):
        """Returns compute node for the host"""
        try:
            return objects.ComputeNode.get_by_name(context, self.host)
        except exception.ComputeNodeNotFound:
            LOG.warning("No compute node record for: %(host)s",
                        {'host': self.host})

    def _get_node_rp_uuid(self, context, node):
        if self.rp_uuid:
            return self.rp_uuid

        if CONF.compute.host_shared_with_nova:
            try:
                self.rp_uuid = self.reportclient.get_provider_by_name(
                    context, node.hostname)['uuid']
            except exception.ResourceProviderNotFound:
                # NOTE(hongbin): cannot find the resource provider created
                # by nova. Probably, the configured hostname in Zun doesn't
                # match the hypervisor_hostname in nova.
                # We give a few more tries with possible hostname.
                possible_rp_names = [socket.gethostname(), socket.getfqdn()]
                for name in possible_rp_names:
                    try:
                        self.rp_uuid = self.reportclient.get_provider_by_name(
                            context, name)['uuid']
                        break
                    except exception.ResourceProviderNotFound:
                        pass

                if not self.rp_uuid:
                    raise exception.ComputeHostNotFound(host=node.hostname)
        else:
            self.rp_uuid = node.uuid

        return self.rp_uuid

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def container_claim(self, context, container, pci_requests, limits=None):
        """Indicate resources are needed for an upcoming container build.

        This should be called before the compute node is about to perform
        an container build operation that will consume additional resources.

        :param context: security context
        :param container: container to reserve resources for.
        :type container: zun.objects.container.Container object
        :param pci_requests: pci requests for sriov port.
        :param limits: Dict of oversubscription limits for memory, disk,
                       and CPUs.
        :returns: A Claim ticket representing the reserved resources.  It can
                  be used to revert the resource usage if an error occurs
                  during the container build.
        """
        # No memory, cpu, disk or pci_request specified, no need to claim
        # resource now.
        if not (container.memory or container.cpu or pci_requests or
                container.disk):
            return claims.NopClaim()

        # We should have the compute node created here, just get it.
        self.compute_node = self._get_compute_node(context)

        claim = claims.Claim(context, container, self, self.compute_node,
                             pci_requests, limits=limits)

        if self.pci_tracker:
            self.pci_tracker.claim_container(context, container.uuid,
                                             pci_requests)

        self._set_container_host(context, container)
        self._update_usage_from_container(context, container)
        # persist changes to the compute node:
        self._update(context, self.compute_node)

        return claim

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def container_update_claim(self, context, new_container, old_container,
                               limits=None):
        """Indicate resources are needed for an upcoming container update.

        This should be called before the compute node is about to perform
        an container update operation that will consume additional resources.

        :param context: security context
        :param new_container: container to be updated to.
        :type new_container: zun.objects.container.Container object
        :param old_container: container to be updated from.
        :type old_container: zun.objects.container.Container object
        :param limits: Dict of oversubscription limits for memory, disk,
                       and CPUs.
        :returns: A Claim ticket representing the reserved resources.  It can
                  be used to revert the resource usage if an error occurs
                  during the container update.
        """
        if (new_container.cpu == old_container.cpu and
                new_container.memory == old_container.memory):
            return claims.NopClaim()

        # We should have the compute node created here, just get it.
        self.compute_node = self._get_compute_node(context)

        claim = claims.UpdateClaim(context, new_container, old_container,
                                   self, self.compute_node, limits=limits)

        self._update_usage_from_container_update(context, new_container,
                                                 old_container)
        # persist changes to the compute node:
        self._update(context, self.compute_node)

        return claim

    def disabled(self, hostname):
        if not self.compute_node:
            return True

        return (hostname != self.compute_node.hostname or
                not self.container_driver.node_is_available(hostname))

    def _set_container_host(self, context, container):
        """Tag the container as belonging to this host.

        This should be done while the COMPUTE_RESOURCES_SEMAPHORE is held so
        the resource claim will not be lost if the audit process starts.
        """
        container.host = self.host
        container.save(context)

    def _update_usage_from_container(self, context, container,
                                     is_removed=False):
        """Update usage for a single container."""

        uuid = container.uuid
        is_new_container = uuid not in self.tracked_containers
        is_removed_container = not is_new_container and is_removed

        if is_new_container:
            self.tracked_containers[uuid] = \
                obj_base.obj_to_primitive(container)
            sign = 1

        if is_removed_container:
            self.tracked_containers.pop(uuid)
            sign = -1

        if is_new_container or is_removed_container:
            if self.pci_tracker:
                self.pci_tracker.update_pci_for_container(context, container,
                                                          sign=sign)

            # new container, update compute node resource usage:
            self._update_usage(self._get_usage_dict(container), sign=sign)

    def _update_usage_from_container_update(self, context, new_container,
                                            old_container):
        """Update usage for a container update."""
        uuid = new_container.uuid
        self.tracked_containers[uuid] = obj_base.obj_to_primitive(
            new_container)
        # update compute node resource usage
        self._update_usage(self._get_usage_dict(old_container), sign=-1)
        self._update_usage(self._get_usage_dict(new_container))

    def _update_usage_from_containers(self, context, containers):
        """Calculate resource usage based on container utilization.

        This is different than the container daemon view as it will account
        for all containers assigned to the local compute host, even if they
        are not currently powered on.
        """
        self.tracked_containers.clear()

        cn = self.compute_node
        # set some initial values, reserve room for host
        cn.cpu_used = 0
        cn.mem_free = cn.mem_total
        cn.mem_used = 0
        cn.running_containers = 0
        cn.disk_used = 0

        for cnt in containers:
            self._update_usage_from_container(context, cnt)

        cn.mem_free = max(0, cn.mem_free)

    def _update_usage(self, usage, sign=1):
        mem_usage = usage['memory']
        cpus_usage = usage.get('cpu', 0)
        disk_usage = usage['disk']
        cpuset_cpus_usage = None
        numa_node_id = 0
        if 'cpuset_cpus' in usage.keys():
            cpuset_cpus_usage = usage['cpuset_cpus']
            numa_node_id = usage['node']

        cn = self.compute_node
        numa_topology = cn.numa_topology.nodes
        cn.mem_used += sign * mem_usage
        cn.cpu_used += sign * cpus_usage
        cn.disk_used += sign * disk_usage

        # free ram may be negative, depending on policy:
        cn.mem_free = cn.mem_total - cn.mem_used

        cn.running_containers += sign * 1

        if cpuset_cpus_usage:
            for numa_node in numa_topology:
                if numa_node.id == numa_node_id:
                    numa_node.mem_available = (numa_node.mem_available -
                                               mem_usage * sign)
                    if sign > 0:
                        numa_node.pin_cpus(cpuset_cpus_usage)
                        cn._changed_fields.add('numa_topology')
                    else:
                        numa_node.unpin_cpus(cpuset_cpus_usage)
                        cn._changed_fields.add('numa_topology')

    def _update(self, context, compute_node):
        if not self._resource_change(compute_node):
            return
        # Persist the stats to the Scheduler
        self.scheduler_client.update_resource(compute_node)

        self._update_to_placement(context, compute_node)

        if self.pci_tracker:
            self.pci_tracker.save()

    def _resource_change(self, compute_node):
        """Check to see if any resources have changed."""
        hostname = compute_node.hostname
        old_compute = self.old_resources[hostname]
        if not obj_base.obj_equal_prims(
                compute_node, old_compute, ['updated_at']):
            self.old_resources[hostname] = copy.deepcopy(compute_node)
            return True
        return False

    @retrying.retry(stop_max_attempt_number=4,
                    retry_on_exception=lambda e: isinstance(
                        e, exception.ResourceProviderUpdateConflict))
    def _update_to_placement(self, context, compute_node):
        """Send resource and inventory changes to placement."""
        node_rp_uuid = self._get_node_rp_uuid(context, compute_node)
        # Persist the stats to the Scheduler
        # First try update_provider_tree
        # Retrieve the provider tree associated with this compute node.  If
        # it doesn't exist yet, this will create it with a (single, root)
        # provider corresponding to the compute node.
        prov_tree = self.reportclient.get_provider_tree_and_ensure_root(
            context, node_rp_uuid, name=compute_node.hostname)
        # Let the container driver rearrange the provider tree and set/update
        # the inventory, traits, and aggregates throughout.
        self.container_driver.update_provider_tree(prov_tree, node_rp_uuid)
        # Inject driver capabilities traits into the provider
        # tree.  We need to determine the traits that the container
        # driver owns - so those that come from the tree itself
        # (via the container driver) plus the compute capabilities
        # traits, and then merge those with the traits set
        # externally that the driver does not own - and remove any
        # set on the provider externally that the driver owns but
        # aren't in the current list of supported traits.  For
        # example, let's say we reported multiattach support as a
        # trait at t1 and then at t2 it's not, so we need to
        # remove it.  But at both t1 and t2 there is a
        # CUSTOM_VENDOR_TRAIT_X which we can't touch because it
        # was set externally on the provider.
        # We also want to sync the COMPUTE_STATUS_DISABLED trait based
        # on the related zun-compute service's disabled status.
        traits = self._get_traits(
            context, node_rp_uuid, provider_tree=prov_tree)
        prov_tree.update_traits(node_rp_uuid, traits)

        self.reportclient.update_from_provider_tree(context, prov_tree)

    def _get_traits(self, context, nodename, provider_tree):
        """Synchronizes internal and external traits for the node provider.

        This works in conjunction with the ComptueDriver.update_provider_tree
        flow and is used to synchronize traits reported by the compute driver,
        traits based on information in the ComputeNode record, and traits set
        externally using the placement REST API.

        :param context: RequestContext for cell database access
        :param nodename: ComputeNode.hostname for the compute node
            resource provider whose traits are being synchronized; the node
            must be in the ProviderTree.
        :param provider_tree: ProviderTree being updated
        """
        # Get the traits from the ProviderTree which will be the set
        # of driver-owned traits plus any externally defined traits set
        # on the provider that aren't owned by the container driver.
        traits = provider_tree.data(nodename).traits

        # Now get the driver's capabilities and add any supported
        # traits that are missing, and remove any existing set traits
        # that are not currently supported.
        # TODO(hongbin): get traits from capsule_driver as well
        capabilities_traits = self.container_driver.capabilities_as_traits()
        for trait, supported in capabilities_traits.items():
            if supported:
                traits.add(trait)
            elif trait in traits:
                traits.remove(trait)

        self._sync_compute_service_disabled_trait(context, traits)

        return list(traits)

    def _sync_compute_service_disabled_trait(self, context, traits):
        """Synchronize the ZUN_COMPUTE_STATUS_DISABLED  trait on the node provider.

        Determines if the ZUN_COMPUTE_STATUS_DISABLED trait should be added to
        or removed from the provider's set of traits based on the related
        zun-compute service disabled status.

        :param context: RequestContext for cell database access
        :param traits: set of traits for the compute node resource provider;
            this is modified by reference
        """
        trait = consts.ZUN_COMPUTE_STATUS_DISABLED
        try:
            service = objects.ZunService.get_by_host_and_binary(
                context, self.host, 'zun-compute')
            if service.disabled:
                # The service is disabled so make sure the trait is reported.
                traits.add(trait)
            else:
                # The service is not disabled so do not report the trait.
                traits.discard(trait)
        except exception.NotFound:
            # This should not happen but handle it gracefully. The scheduler
            # should ignore this node if the compute service record is gone.
            LOG.error('Unable to find services table record for zun-compute '
                      'host %s', self.host)

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def _update_available_resource(self, context):

        # if we could not init the compute node the tracker will be
        # disabled and we should quit now
        if self.disabled(self.host):
            return

        # Grab all containers assigned to this node:
        containers = objects.Container.list_by_host(context, self.host)
        capsules = objects.Capsule.list_by_host(context, self.host)

        # Now calculate usage based on container utilization:
        self._update_usage_from_containers(context, containers + capsules)

        # No migration for docker, is there will be orphan container? Nova has.

        cn = self.compute_node

        # update the compute_node
        self._update(context, cn)
        LOG.debug('Compute_service record updated for %(host)s',
                  {'host': self.host})

    def _get_usage_dict(self, container, **updates):
        """Make a usage dict _update methods expect.

        Accepts an Container, and a set of updates.
        Converts the object to a dict and applies the updates.

        :param container: container as an object
        :param updates: key-value pairs to update the passed object.

        :returns: a dict with all the information from container updated
                  with updates
        """
        usage = {}
        # (Fixme): The Container.memory is string.
        memory = 0
        if container.memory:
            memory = int(container.memory)
        usage = {'memory': memory,
                 'cpu': container.cpu or 0,
                 'disk': container.disk or 0}
        if container.cpuset.cpuset_cpus:
            usage['cpuset_cpus'] = container.cpuset.cpuset_cpus
            usage['node'] = int(container.cpuset.cpuset_mems)

        return usage

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def abort_container_claim(self, context, container):
        """Remove usage from the given container."""
        self._update_usage_from_container(context, container, is_removed=True)

        self._update(context, self.compute_node)

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def abort_container_update_claim(self, context, new_container,
                                     old_container):
        """Remove usage from the given container."""
        self._update_usage_from_container_update(context, old_container,
                                                 new_container)
        self._update(self.compute_node)

    @utils.synchronized(COMPUTE_RESOURCE_SEMAPHORE)
    def remove_usage_from_container(self, context, container,
                                    is_removed=True):
        """Just a wrapper of the private function to hold lock."""

        # We need to get the latest compute node info
        self.compute_node = self._get_compute_node(context)
        self._update_usage_from_container(context, container, is_removed)
        self._update(context, self.compute_node)
