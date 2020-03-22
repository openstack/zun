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

"""
The FilterScheduler is for scheduling container to a host according to
your filters configured.
You can customize this scheduler by specifying your own Host Filters.
"""

from oslo_log.log import logging

from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun import objects
from zun.scheduler.client import report
from zun.scheduler import driver
from zun.scheduler import filters
from zun.scheduler.host_state import HostState
from zun.scheduler import utils


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class FilterScheduler(driver.Scheduler):
    """Scheduler that can be used for filtering zun compute."""

    def __init__(self):
        super(FilterScheduler, self).__init__()
        self.filter_handler = filters.HostFilterHandler()
        filter_classes = self.filter_handler.get_matching_classes(
            CONF.scheduler.available_filters)
        self.filter_cls_map = {cls.__name__: cls for cls in filter_classes}
        self.filter_obj_map = {}
        self.enabled_filters = self._choose_host_filters(self._load_filters())
        self.placement_client = report.SchedulerReportClient()

    def _schedule(self, context, container, extra_specs, alloc_reqs_by_rp_uuid,
                  provider_summaries, allocation_request_version=None):
        """Picks a host according to filters."""
        elevated = context.elevated()

        # NOTE(jaypipes): provider_summaries being None is treated differently
        # from an empty dict. provider_summaries is None when we want to grab
        # all compute nodes.
        # The provider_summaries variable will be an empty dict when the
        # Placement API found no providers that match the requested
        # constraints, which in turn makes compute_uuids an empty list and
        # objects.ComputeNode.list will return an empty list
        # also, which will eventually result in a NoValidHost error.
        compute_uuids = None
        if provider_summaries is not None:
            compute_uuids = list(provider_summaries.keys())
        if compute_uuids is None:
            nodes = objects.ComputeNode.list(context)
        else:
            nodes = objects.ComputeNode.list(
                context, filters={'rp_uuid': compute_uuids})

        services = self._get_services_by_host(context)
        hosts = services.keys()
        nodes = [node for node in nodes if node.hostname in hosts]
        host_states = self.get_all_host_state(nodes, services)
        hosts = self._get_filtered_hosts(host_states, container, extra_specs)
        if not hosts:
            msg = _("Is the appropriate service running?")
            raise exception.NoValidHost(reason=msg)

        # Attempt to claim the resources against one or more resource
        # providers, looping over the sorted list of possible hosts
        # looking for an allocation_request that contains that host's
        # resource provider UUID
        claimed_host = None
        for host in hosts:
            cn_uuid = host.uuid
            if cn_uuid not in alloc_reqs_by_rp_uuid:
                msg = ("A host state with uuid = '%s' that did not have a "
                       "matching allocation_request was encountered while "
                       "scheduling. This host was skipped.")
                LOG.debug(msg, cn_uuid)
                continue

            alloc_reqs = alloc_reqs_by_rp_uuid[cn_uuid]
            # TODO(jaypipes): Loop through all allocation_requests instead
            # of just trying the first one. For now, since we'll likely
            # want to order the allocation_requests in the future based on
            # information in the provider summaries, we'll just try to
            # claim resources using the first allocation_request
            alloc_req = alloc_reqs[0]
            if utils.claim_resources(
                    elevated, self.placement_client, container, alloc_req,
                    allocation_request_version=allocation_request_version):
                claimed_host = host
                break

        if claimed_host is None:
            # We weren't able to claim resources in the placement API
            # for any of the sorted hosts identified. So, clean up any
            # successfully-claimed resources for prior containers in
            # this request and return an empty list which will cause
            # select_destinations() to raise NoValidHost
            msg = _("Unable to successfully claim against any host.")
            raise exception.NoValidHost(reason=msg)

        # Now consume the resources so the filter/weights will change for
        # the next container.
        self._consume_selected_host(claimed_host, container)

        return claimed_host

    def _get_filtered_hosts(self, hosts, container, extra_specs):
        """Filter hosts and return only ones passing all filters."""

        def _get_hosts_matching_request(hosts, requested_host):
            matched_hosts = [x for x in hosts
                             if x.hostname == requested_host]
            if matched_hosts:
                LOG.info('Host filter only checking host %(host)s',
                         {'host': requested_host})
            else:
                # NOTE(hongbin): The API level should prevent the user from
                # providing a wrong requested host but let's make sure a wrong
                # destination doesn't trample the scheduler still.
                LOG.info('No hosts matched due to not matching requested '
                         'destination (%(host)s)', {'host': requested_host})
            return iter(matched_hosts)

        requested_host = extra_specs.get('requested_host', [])

        if requested_host:
            # NOTE(hongbin): Reduce a potentially long set of hosts as much as
            # possible to any requested destination nodes before passing the
            # list to the filters
            hosts = _get_hosts_matching_request(hosts, requested_host)

        return self.filter_handler.get_filtered_objects(
            self.enabled_filters, hosts, container, extra_specs)

    def select_destinations(self, context, containers, extra_specs,
                            alloc_reqs_by_rp_uuid, provider_summaries,
                            allocation_request_version=None):
        """Selects destinations by filters."""
        dests = []
        for container in containers:
            host = self._schedule(context, container, extra_specs,
                                  alloc_reqs_by_rp_uuid, provider_summaries,
                                  allocation_request_version)
            host_state = dict(host=host.hostname, nodename=None,
                              limits=host.limits)
            dests.append(host_state)

        if len(dests) < 1:
            reason = _('There are not enough hosts available.')
            raise exception.NoValidHost(reason=reason)

        return dests

    def _choose_host_filters(self, filter_cls_names):
        """Choose good filters

        Since the caller may specify which filters to use we need
        to have an authoritative list of what is permissible. This
        function checks the filter names against a predefined set
        of acceptable filters.
        """
        if not isinstance(filter_cls_names, (list, tuple)):
            filter_cls_names = [filter_cls_names]

        good_filters = []
        bad_filters = []
        for filter_name in filter_cls_names:
            if filter_name not in self.filter_obj_map:
                if filter_name not in self.filter_cls_map:
                    bad_filters.append(filter_name)
                    continue
                filter_cls = self.filter_cls_map[filter_name]
                self.filter_obj_map[filter_name] = filter_cls()
            good_filters.append(self.filter_obj_map[filter_name])
        if bad_filters:
            msg = ", ".join(bad_filters)
            raise exception.SchedulerHostFilterNotFound(filter_name=msg)
        return good_filters

    def _load_filters(self):
        return CONF.scheduler.enabled_filters

    def _get_services_by_host(self, context):
        """Get a dict of services indexed by hostname"""
        return {service.host: service
                for service in objects.ZunService.list_by_binary(
                    context,
                    'zun-compute')}

    def get_all_host_state(self, nodes, services):
        host_states = []
        for node in nodes:
            host_state = HostState(node.hostname)
            host_state.update(compute_node=node,
                              service=services.get(node.hostname))
            host_states.append(host_state)
        return host_states

    @staticmethod
    def _consume_selected_host(selected_host, container):
        LOG.debug("Selected host: %(host)s", {'host': selected_host})
        selected_host.consume_from_request(container)
