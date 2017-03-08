# Copyright 2017 IBM Corp
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

from zun.common import utils
from zun import objects


class Host(object):

    def __init__(self):
        self.capabilities = None

    def get_cpu_numa_info(self):
        """This method returns a dict containing the cpuset info for a host"""

        raise NotImplementedError()

    def get_host_numa_topology(self, numa_topo_obj):
        # Replace this call with a more generic call when we obtain other
        # NUMA related data like memory etc.
        cpu_info = self.get_cpu_numa_info()
        floating_cpus = utils.get_floating_cpu_set()
        numa_node_obj = []
        for node, cpuset in cpu_info.items():
            numa_node = objects.NUMANode()
            if floating_cpus:
                allowed_cpus = set(cpuset) - (floating_cpus & set(cpuset))
            else:
                allowed_cpus = set(cpuset)
            numa_node.id = node
            # allowed_cpus are the ones allowed to pin on.
            # Rest of the cpus are assumed to be floating
            # in nature.
            numa_node.cpuset = allowed_cpus
            numa_node.pinned_cpus = set([])
            numa_node_obj.append(numa_node)
        numa_topo_obj.nodes = numa_node_obj
