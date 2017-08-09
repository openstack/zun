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


class CPUFilter(filters.BaseHostFilter):
    """Filter the containers by cpu request"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        if not container.cpu:
            return True

        cpu_free = host_state.cpus - host_state.cpu_used
        if cpu_free < container.cpu:
            LOG.debug("%(host_state)s does not have %(container_vcpus).2f "
                      "usable vcpus, it only has %(free_vcpus).2f usable "
                      "vcpus",
                      {'host_state': host_state,
                       'container_vcpus': container.cpu,
                       'free_vcpus': cpu_free})
            return False
        host_state.limits['cpu'] = host_state.cpus
        return True
