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

import re

from oslo_log.log import logging

from zun.common import context as zun_context
from zun.scheduler import filters
from zun.scheduler.client import report

LOG = logging.getLogger(__name__)

BLAZAR_PLACEMENT_TRAIT_PATTERN = "^CUSTOM_RESERVATION_([A-Z0-9_]*)_PROJECT_([A-Z0-9_]*)$"


class BlazarFilter(filters.BaseHostFilter):
    """Filter on Blazar reserved nodes"""

    def __init__(self):
        self.placement_client = report.SchedulerReportClient()
        super(BlazarFilter, self).__init__()

    run_filter_once_per_request = True

    def host_passes(self, host_state, container, extra_spec):
        """Check if a host has a blazar placement trait can be used for a request

        A host has a custom blazar placement trait

        If the user does not pass "reservation=<id>" as a hint then only
        hosts which don't have any custom blazar placement trait pass.

        If the user does pass "reservation=<id>" as a hint then the host only
        passes if it has a custom placement trait that:
            - follows the blazar_placement_trait_pattern
            - reservation id matches the reservation id in the trait name
            - project id matches the project id in the trait name
        """
        hints = extra_spec.get('hints', {})
        reservation_id = hints.get('reservation')
        project_id = container.project_id

        blazar_rp = self.placement_client.get_provider_by_name(
            zun_context.get_admin_context(), "blazar_" + host_state.hostname)

        traits = self.placement_client.get_provider_traits(
            zun_context.get_admin_context(), blazar_rp['uuid']).traits

        if not reservation_id:
            # user does not pass reservation as a hint
            for trait in traits:
                if re.search(BLAZAR_PLACEMENT_TRAIT_PATTERN, trait):
                    return False
            return True
        else:
            # user does pass reservation as a hint
            for trait in traits:
                match = re.search(BLAZAR_PLACEMENT_TRAIT_PATTERN, trait)
                if match:
                    trait_rid = match.group(1).lower().replace('_', '-')
                    trait_pid = match.group(2).lower().replace('_', '-')
                    if (trait_rid == reservation_id and
                            trait_pid == project_id):
                        return True
            return False
