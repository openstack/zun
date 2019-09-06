# Copyright (c) 2014 Red Hat, Inc.
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

import collections

from keystoneauth1 import exceptions as ks_exc
from oslo_log import log as logging
from stevedore import driver

from zun.common import consts
from zun.common import exception
import zun.conf
from zun.scheduler.client import report
from zun.scheduler import request_filter
from zun.scheduler import utils


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class SchedulerClient(object):
    """Client library for placing calls to the scheduler."""

    def __init__(self):
        self.placement_client = report.SchedulerReportClient()
        scheduler_driver = CONF.scheduler.driver
        self.driver = driver.DriverManager(
            "zun.scheduler.driver",
            scheduler_driver,
            invoke_on_load=True).driver
        self.traits_ensured = False

    def select_destinations(self, context, containers, extra_specs):
        LOG.debug("Starting to schedule for containers: %s",
                  [c.uuid for c in containers])

        if not self.traits_ensured:
            self.placement_client._ensure_traits(context, consts.CUSTOM_TRAITS)
            self.traits_ensured = True

        alloc_reqs_by_rp_uuid, provider_summaries, allocation_request_version \
            = None, None, None
        request_filter.process_reqspec(context, extra_specs)
        resources = utils.resources_from_request_spec(
            context, containers[0], extra_specs)

        try:
            res = self.placement_client.get_allocation_candidates(context,
                                                                  resources)
            (alloc_reqs, provider_summaries, allocation_request_version) = res
        except (ks_exc.EndpointNotFound,
                ks_exc.MissingAuthPlugin,
                ks_exc.Unauthorized,
                ks_exc.DiscoveryFailure,
                ks_exc.ConnectFailure):
            # We have to handle the case that we failed to connect to the
            # Placement service.
            alloc_reqs, provider_summaries, allocation_request_version = (
                None, None, None)
        if not alloc_reqs:
            LOG.info("Got no allocation candidates from the Placement "
                     "API. This could be due to insufficient resources "
                     "or a temporary occurrence as compute nodes start "
                     "up.")
            raise exception.NoValidHost(reason="")
        else:
            # Build a dict of lists of allocation requests, keyed by
            # provider UUID, so that when we attempt to claim resources for
            # a host, we can grab an allocation request easily
            alloc_reqs_by_rp_uuid = collections.defaultdict(list)
            for ar in alloc_reqs:
                for rp_uuid in ar['allocations']:
                    alloc_reqs_by_rp_uuid[rp_uuid].append(ar)

        selections = self.driver.select_destinations(
            context, containers, extra_specs, alloc_reqs_by_rp_uuid,
            provider_summaries, allocation_request_version)
        return selections

    def update_resource(self, node):
        node.save()
        # TODO(Shunli): Update the inventory here
