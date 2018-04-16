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

from oslo_log import log as logging

from zun.scheduler import filters

LOG = logging.getLogger(__name__)


class RamFilter(filters.BaseHostFilter):
    """Filter the containers by memory request"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        if not container.memory:
            return True

        request_ram = int(container.memory)
        usable_ram = host_state.mem_total - host_state.mem_used
        if usable_ram < request_ram:
            LOG.debug("%(host_state)s does not have %(request_ram)d "
                      "usable memory, it only has %(usable_ram)d usable "
                      "memory.",
                      {'host_state': host_state,
                       'request_ram': request_ram,
                       'usable_ram': usable_ram})
            return False
        host_state.limits['memory'] = host_state.mem_total
        return True
