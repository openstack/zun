# Copyright 2015 OpenStack Foundation
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

from oslo_config import cfg


scheduler_group = cfg.OptGroup(name="scheduler",
                               title="Scheduler configuration")

scheduler_opts = [
    cfg.StrOpt("driver",
               default="filter_scheduler",
               choices=("chance_scheduler", "fake_scheduler",
                        "filter_scheduler"),
               help="""
The class of the driver used by the scheduler.

The options are chosen from the entry points under the namespace
'zun.scheduler.driver' in 'setup.cfg'.

Possible values:

* A string, where the string corresponds to the class name of a scheduler
  driver. There are a number of options available:
** 'chance_scheduler', which simply picks a host at random
** A custom scheduler driver. In this case, you will be responsible for
   creating and maintaining the entry point in your 'setup.cfg' file
"""),
    cfg.MultiStrOpt("available_filters",
                    default=["zun.scheduler.filters.all_filters"],
                    help="""
Filters that the scheduler can use.

An unordered list of the filter classes the zun scheduler may apply.  Only the
filters specified in the 'scheduler_enabled_filters' option will be used, but
any filter appearing in that option must also be included in this list.

By default, this is set to all filters that are included with zun.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect.

Possible values:

* A list of zero or more strings, where each string corresponds to the name of
  a filter that may be used for selecting a host

Related options:

* scheduler_enabled_filters
"""),
    cfg.ListOpt("enabled_filters",
                default=[
                    "AvailabilityZoneFilter",
                    "ComputeFilter",
                    "RuntimeFilter",
                    ],
                help="""
Filters that the scheduler will use.

An ordered list of filter class names that will be used for filtering
hosts. Ignore the word 'default' in the name of this option: these filters will
*always* be applied, and they will be applied in the order they are listed so
place your most restrictive filters first to make the filtering process more
efficient.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect.

Possible values:

* A list of zero or more strings, where each string corresponds to the name of
  a filter to be used for selecting a host

Related options:

* All of the filters in this option *must* be present in the
  'scheduler_available_filters' option, or a SchedulerHostFilterNotFound
  exception will be raised.
"""),
    cfg.IntOpt("max_placement_results",
               default=1000,
               min=1,
               help="""
This setting determines the maximum limit on results received from the
placement service during a scheduling operation. It effectively limits
the number of hosts that may be considered for scheduling requests that
match a large number of candidates.

A value of 1 (the minimum) will effectively defer scheduling to the placement
service strictly on "will it fit" grounds. A higher value will put an upper
cap on the number of results the scheduler will consider during the filtering
and weighing process. Large deployments may need to set this lower than the
total number of hosts available to limit memory consumption, network traffic,
etc. of the scheduler.

This option is only used by the FilterScheduler; if you use a different
scheduler, this option has no effect.
"""),
]


def register_opts(conf):
    conf.register_group(scheduler_group)
    conf.register_opts(scheduler_opts, group=scheduler_group)


def list_opts():
    return {scheduler_group: scheduler_opts}
