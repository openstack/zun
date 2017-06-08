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
        self.numa_topology = None

        # Resource oversubscription values for the compute host:
        self.limits = {}
