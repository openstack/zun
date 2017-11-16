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


class LabelFilter(filters.BaseHostFilter):
    """Filter the containers by label"""

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        labels = {}
        for key, value in extra_spec['hints'].items():
            if key.startswith('label:'):
                newkey = key[6:]
                labels[newkey] = value

        if not labels:
            return True

        for key in labels:
            if not(key in host_state.labels and
                   host_state.labels.get(key) == labels.get(key)):
                LOG.debug("%(host_state)s does not have labels"
                          " %(key)s=%(value)s that container %(container)s"
                          " required.",
                          {'host_state': host_state,
                           'key': key,
                           'value': labels.get(key),
                           'container': container.name})
                return False

        return True
