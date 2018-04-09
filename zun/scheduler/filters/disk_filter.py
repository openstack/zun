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


class DiskFilter(filters.BaseHostFilter):
    """Filter the containers by disk request"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        if not hasattr(container, 'disk') or not container.disk:
            return True

        if not host_state.disk_quota_supported:
            LOG.debug("(%(host_state)s) does not support disk quota, but the "
                      "container requires disk quota of %(container_disk)d.",
                      {'host_state': host_state,
                       'container_disk': container.disk})
            return False

        usable_disk = host_state.disk_total - host_state.disk_used
        if usable_disk < container.disk:
            LOG.debug("%(host_state)s does not have %(container_disk)d "
                      "usable disk, it only has %(usable_disk)d usable "
                      "disk.",
                      {'host_state': host_state,
                       'container_disk': container.disk,
                       'usable_disk': usable_disk})
            return False
        host_state.limits['disk'] = host_state.disk_total
        return True
