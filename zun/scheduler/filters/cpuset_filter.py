#    Copyright (c) 2018 National Engineering Laboratory of electronic
#    commerce and electronic payment
#    All Rights Reserved.
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

from oslo_log import log as logging

import zun.conf
from zun.scheduler import filters

LOG = logging.getLogger(__name__)
CONF = zun.conf.CONF


class CpuSetFilter(filters.BaseHostFilter):
    """Filter the host by cpu and memory request of cpuset"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        if container.cpu_policy is None:
            container.cpu_policy = 'shared'
        if container.memory is None:
            container_memory = 0
        else:
            container_memory = int(container.memory)
        if container.cpu_policy == 'dedicated':
            if host_state.enable_cpu_pinning:
                for numa_node in host_state.numa_topology.nodes:
                    if len(numa_node.cpuset) - len(
                            numa_node.pinned_cpus) >= container.cpu and \
                            numa_node.mem_available >= container_memory:
                        host_state.limits['cpuset'] = {
                            'node': numa_node.id,
                            'cpuset_cpu': numa_node.cpuset,
                            'cpuset_cpu_pinned': numa_node.pinned_cpus,
                            'cpuset_mem': numa_node.mem_available
                        }
                        return True
                return False
            else:
                return False
        if container.cpu_policy == 'shared':
            if CONF.compute.enable_cpu_pinning:
                return False
            else:
                return True
