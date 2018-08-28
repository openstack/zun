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


class RuntimeFilter(filters.BaseHostFilter):
    """Filter the containers by runtime"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        if not hasattr(container, 'runtime') or not container.runtime:
            return True

        if container.runtime not in host_state.runtimes:
            LOG.debug("Runtime '%(container_runtime)s' requested. "
                      "%(host_state)s has runtimes: %(host_runtime)s",
                      {'host_state': host_state,
                       'container_runtime': container.runtime,
                       'host_runtime': host_state.runtimes})
            return False
        return True
