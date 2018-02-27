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


class AvailabilityZoneFilter(filters.BaseHostFilter):
    """Filters Hosts by availability zone."""

    # Availability zones do not change within a request
    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        availability_zone = extra_spec.get('availability_zone') or \
            CONF.default_schedule_zone
        if not availability_zone:
            return True

        host_az = host_state.service.availability_zone
        if not host_az:
            host_az = CONF.default_availability_zone

        hosts_passes = availability_zone == host_az
        if not hosts_passes:
            LOG.debug("Availability Zone '%(az)s' requested. "
                      "%(host_state)s has AZs: %(host_az)s",
                      {'host_state': host_state,
                       'az': availability_zone,
                       'host_az': host_az})

        return hosts_passes
