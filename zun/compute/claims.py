# Copyright (c) 2017 OpenStack Foundation
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

"""
Claim objects for use with resource tracking.
"""

from oslo_log import log as logging

from zun.common import exception
from zun.common.i18n import _

LOG = logging.getLogger(__name__)


class NopClaim(object):
    """For use with compute drivers that do not support resource tracking."""

    def __init__(self, *args, **kwargs):
        self.claimed_numa_topology = None

    @property
    def memory(self):
        return 0

    @property
    def cpu(self):
        return 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.abort()

    def abort(self):
        pass

    def __str__(self):
        return "[Claim: %s memory, %.2f VCPU]" % (self.memory,
                                                  self.cpu)


class Claim(NopClaim):
    """A declaration that a compute host operation will require free resources.

    Claims serve as marker objects that resources are being held until the
    update_available_resource audit process runs to do a full reconciliation
    of resource usage.

    This information will be used to help keep the local compute hosts's
    ComputeNode model in sync to aid the scheduler in making efficient / more
    correct decisions with respect to host selection.
    """

    def __init__(self, context, container, tracker, resources, pci_requests,
                 limits=None):
        super(Claim, self).__init__()
        # Stash a copy of the container at the current point of time
        self.container = container.obj_clone()
        self._numa_topology_loaded = False
        self.tracker = tracker
        self.context = context
        self._pci_requests = pci_requests

        # Check claim at constructor to avoid mess code
        # Raise exception ComputeResourcesUnavailable if claim failed
        self._claim_test(resources, limits)

    @property
    def memory(self):
        mem_str = "0"
        if self.container.memory:
            mem_str = self.container.memory[:-1]
        return int(mem_str)

    @property
    def cpu(self):
        return self.container.cpu or 0

    def abort(self):
        """Requiring claimed resources has failed or been aborted."""
        LOG.debug("Aborting claim: %s", self)
        self.tracker.abort_container_claim(self.context, self.container)

    def _claim_test(self, resources, limits=None):
        """Test if this claim can be satisfied.

        With given available resources and optional oversubscription limits

        This should be called before the compute node actually consumes the
        resources required to execute the claim.

        :param resources: available local compute node resources
        :returns: Return true if resources are available to claim.
        """
        if not limits:
            limits = {}

        # If an individual limit is None, the resource will be considered
        # unlimited:
        memory_limit = limits.get('memory')
        cpu_limit = limits.get('cpu')

        LOG.info('Attempting claim: memory %(memory)s, '
                 'cpu %(cpu).02f CPU',
                 {'memory': self.memory, 'cpu': self.cpu})

        reasons = [self._test_memory(resources, memory_limit),
                   self._test_cpu(resources, cpu_limit),
                   self._test_pci()]
        # TODO(Shunli): test numa here
        reasons = [r for r in reasons if r is not None]
        if len(reasons) > 0:
            raise exception.ResourcesUnavailable(reason="; ".join(reasons))

        LOG.info('Claim successful')

    def _test_pci(self):
        pci_requests = self._pci_requests
        if pci_requests and pci_requests.requests:
            stats = self.tracker.pci_tracker.stats
            if not stats.support_requests(pci_requests.requests):
                return _('Claim pci failed')

    def _test_memory(self, resources, limit):
        type_ = _("memory")
        unit = "MB"
        total = resources.mem_total
        used = resources.mem_used
        requested = self.memory

        return self._test(type_, unit, total, used, requested, limit)

    def _test_cpu(self, resources, limit):
        type_ = _("vcpu")
        unit = "VCPU"
        total = resources.cpus
        used = resources.cpu_used
        requested = self.cpu

        return self._test(type_, unit, total, used, requested, limit)

    def _test(self, type_, unit, total, used, requested, limit):
        """Test if the type resource needed for a claim can be allocated."""

        LOG.info('Total %(type)s: %(total)d %(unit)s, used: %(used).02f '
                 '%(unit)s',
                 {'type': type_, 'total': total, 'unit': unit, 'used': used})

        if limit is None:
            # treat resource as unlimited:
            LOG.info('%(type)s limit not specified, defaulting to '
                     'unlimited', {'type': type_})
            return

        free = limit - used

        # Oversubscribed resource policy info:
        LOG.info('%(type)s limit: %(limit).02f %(unit)s, '
                 'free: %(free).02f %(unit)s',
                 {'type': type_, 'limit': limit, 'free': free, 'unit': unit})

        if requested > free:
            return (_('Free %(type)s %(free).02f '
                      '%(unit)s < requested %(requested)s %(unit)s') %
                    {'type': type_, 'free': free, 'unit': unit,
                     'requested': requested})
