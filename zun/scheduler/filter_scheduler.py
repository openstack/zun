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
import random

from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun import objects
from zun.scheduler import driver
from zun.scheduler import filters


CONF = zun.conf.CONF


class FilterScheduler(driver.Scheduler):
    """Scheduler that can be used for filtering zun compute."""

    def __init__(self, *args, **kwargs):
        super(FilterScheduler, self).__init__(*args, **kwargs)
        self.filter_handler = filters.HostFilterHandler()
        filter_classes = self.filter_handler.get_matching_classes(
            CONF.scheduler.available_filters)
        self.filter_cls_map = {cls.__name__: cls for cls in filter_classes}
        self.filter_obj_map = {}
        self.enabled_filters = self._choose_host_filters(self._load_filters())

    def _schedule(self, context, container, extra_spec):
        """Picks a host according to filters."""
        hosts = self.hosts_up(context)
        nodes = objects.ComputeNode.list(context)
        nodes = [node for node in nodes if node.hostname in hosts]
        nodes = self.filter_handler.get_filtered_objects(self.enabled_filters,
                                                         nodes,
                                                         container,
                                                         extra_spec)
        if not nodes:
            msg = _("Is the appropriate service running?")
            raise exception.NoValidHost(reason=msg)

        return random.choice(nodes)

    def select_destinations(self, context, containers, extra_spec):
        """Selects destinations by filters."""
        dests = []
        for container in containers:
            node = self._schedule(context, container, extra_spec)
            host_state = dict(host=node.hostname, nodename=None, limits=None)
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
