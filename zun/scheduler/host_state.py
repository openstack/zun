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

from oslo_log.log import logging

from zun.common import utils
from zun.pci import stats as pci_stats

LOG = logging.getLogger(__name__)


class HostState(object):
    """Mutable and immutable information tracked for a host.

    This is an attempt to remove the ad-hoc data structures.
    """

    def __init__(self, host):
        self.hostname = host

        # Mutable available resources.
        # These will change as resources are virtually "consumed".
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

        # Resource oversubscription values for the compute host:
        self.limits = {}

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

    def __repr__(self):
        return ("%(host)s ram: %(free_ram)sMB "
                "disk: %(free_disk)sGB cpus: %(free_cpu)s" %
                {'host': self.hostname,
                 'free_ram': self.mem_free,
                 'free_disk': self.disk_total - self.disk_used,
                 'free_cpu': self.cpus - self.cpu_used})
