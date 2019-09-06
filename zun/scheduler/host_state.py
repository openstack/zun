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

import functools

from oslo_log.log import logging
from oslo_utils import timeutils

from zun.common import utils
from zun.pci import stats as pci_stats

LOG = logging.getLogger(__name__)


class HostState(object):
    """Mutable and immutable information tracked for a host.

    This is an attempt to remove the ad-hoc data structures.
    """

    def __init__(self, host):
        self.hostname = host
        self._lock_name = host
        self.uuid = None

        # Mutable available resources.
        # These will change as resources are virtually "consumed".
        self.mem_available = 0
        self.mem_total = 0
        self.mem_free = 0
        self.mem_used = 0
        self.cpus = 0
        self.cpu_used = 0
        self.disk_total = 0
        self.disk_used = 0
        self.numa_topology = None
        self.labels = None
        self.pci_stats = None
        self.disk_quota_supported = False
        self.runtimes = []
        self.enable_cpu_pinning = False

        # Resource oversubscription values for the compute host:
        self.limits = {}

        self.updated = None

    def update(self, compute_node=None, service=None):
        """Update information about a host"""
        @utils.synchronized((self.hostname, compute_node))
        def _locked_update(self, compute_node, service):
            if compute_node is not None:
                LOG.debug('Update host state from compute node: %s',
                          compute_node)
                self._update_from_compute_node(compute_node)
            if service is not None:
                LOG.debug('Update host state with service: %s', service)
                self.service = service

        return _locked_update(self, compute_node, service)

    def _update_from_compute_node(self, compute_node):
        """Update information about a host from a Compute object"""
        if (self.updated and compute_node.updated_at and
                self.updated > compute_node.updated_at):
            return

        self.uuid = compute_node.rp_uuid
        self.mem_available = compute_node.mem_available
        self.mem_total = compute_node.mem_total
        self.mem_free = compute_node.mem_free
        self.mem_used = compute_node.mem_used
        self.cpus = compute_node.cpus
        self.cpu_used = compute_node.cpu_used
        self.disk_total = compute_node.disk_total
        self.disk_used = compute_node.disk_used
        self.numa_topology = compute_node.numa_topology
        self.labels = compute_node.labels
        self.pci_stats = pci_stats.PciDeviceStats(
            stats=compute_node.pci_device_pools)
        self.disk_quota_supported = compute_node.disk_quota_supported
        self.runtimes = compute_node.runtimes
        self.enable_cpu_pinning = compute_node.enable_cpu_pinning
        self.updated = compute_node.updated_at

    def consume_from_request(self, container):
        """Incrementally update host state from a Container object."""

        @utils.synchronized(self._lock_name)
        @set_update_time_on_success
        def _locked(self, container):
            # Scheduler API is inherently multi-threaded as every incoming RPC
            # message will be dispatched in its own green thread. So the
            # shared host state should be consumed in a consistent way to make
            # sure its data is valid under concurrent write operations.
            self._locked_consume_from_request(container)

        return _locked(self, container)

    def _locked_consume_from_request(self, container):
        disk = container.disk if container.disk else 0
        ram_mb = int(container.memory) if container.memory else 0
        vcpus = container.cpu if container.cpu else 0
        self.mem_used += ram_mb
        self.disk_used += disk
        self.cpu_used += vcpus
        self.mem_free = self.mem_total - self.mem_used
        # TODO(hongbin): track numa_topology and pci devices

    def __repr__(self):
        return ("%(host)s ram: %(free_ram)sMB "
                "disk: %(free_disk)sGB cpus: %(free_cpu)s" %
                {'host': self.hostname,
                 'free_ram': self.mem_free,
                 'free_disk': self.disk_total - self.disk_used,
                 'free_cpu': self.cpus - self.cpu_used})


@utils.expects_func_args('self', 'container')
def set_update_time_on_success(function):
    """Set updated time of HostState when consuming succeed."""

    @functools.wraps(function)
    def decorated_function(self, container):
        return_value = None
        try:
            return_value = function(self, container)
        except Exception as e:
            # Ignores exception raised from consume_from_request() so that
            # booting container would fail in the resource claim of compute
            # node, other suitable node may be chosen during scheduling retry.
            LOG.warning("Selected host: %(host)s failed to consume from "
                        "container. Error: %(error)s",
                        {'host': self.hostname, 'error': e})
        else:
            self.updated = timeutils.utcnow()
        return return_value

    return decorated_function
