#    Copyright 2016 IBM Corp.
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


compute_opts = [
    cfg.BoolOpt(
        'resume_container_state',
        default=False,
        help='restart the containers which are running '
             'before the host reboots.'),
    cfg.BoolOpt(
        'remount_container_volume',
        default=True,
        help='remount the volumes of the containers when zun-compute '
             'restarts.'),
    cfg.FloatOpt(
        'reserve_disk_for_image',
        default=0.2,
        help='reserve disk for docker images'),
    cfg.BoolOpt(
        'enable_cpu_pinning',
        default=False,
        help='allow the container with cpu_policy is dedicated'),
    cfg.IntOpt(
        'resource_provider_association_refresh',
        default=300,
        min=0,
        mutable=True,
        # TODO(efried): Provide more/better explanation of what this option is
        # all about. Reference bug(s). Unless we're just going to remove it.
        help="""
Interval for updating zun-compute-side cache of the compute node resource
provider's inventories, aggregates, and traits.
This option specifies the number of seconds between attempts to update a
provider's inventories, aggregates and traits in the local cache of the compute
node.
A value of zero disables cache refresh completely.
The cache can be cleared manually at any time by sending SIGHUP to the compute
process, causing it to be repopulated the next time the data is accessed.
Possible values:
* Any positive integer in seconds, or zero to disable refresh.
"""),
    cfg.BoolOpt(
        'host_shared_with_nova',
        default=False,
        help='Whether this compute node is shared with nova'),
]

service_opts = [
    cfg.StrOpt(
        'topic',
        default='zun-compute',
        help='The queue to add compute tasks to.'),
]

db_opts = [
    cfg.StrOpt(
        'unique_container_name_scope',
        default='',
        choices=['', 'project', 'global'],
        help="""
Sets the scope of the check for unique container names.
The default doesn't check for unique names. If a scope for the name check is
set, a launch of a new container with a duplicate name will result in an
''ContainerAlreadyExists'' error. The uniqueness is case-insensitive.
Setting this option can increase the usability for end users as they don't
have to distinguish among containers with the same name by their IDs.
Possible values:
* '': An empty value means that no uniqueness check is done and duplicate
  names are possible.
* "project": The container name check is done only for containers within the
  same project.
* "global": The container name check is done for all containers regardless of
  the project.
"""),
]

resource_tracker_opts = [
    cfg.IntOpt('reserved_host_disk_mb',
               min=0,
               default=0,
               help="""
Amount of disk resources in MB to make them always available to host. The
disk usage gets reported back to the scheduler from zun-compute running
on the compute nodes. To prevent the disk resources from being considered
as available, this option can be used to reserve disk space for that host.
Possible values:
* Any positive integer representing amount of disk in MB to reserve
  for the host.
"""),
    cfg.IntOpt('reserved_host_memory_mb',
               default=512,
               min=0,
               help="""
Amount of memory in MB to reserve for the host so that it is always available
to host processes. The host resources usage is reported back to the scheduler
continuously from zun-compute running on the compute node. To prevent the host
memory from being considered as available, this option is used to reserve
memory for the host.
Possible values:
* Any positive integer representing amount of memory in MB to reserve
  for the host.
"""),
    cfg.IntOpt('reserved_host_cpus',
               default=0,
               min=0,
               help="""
Number of physical CPUs to reserve for the host. The host resources usage is
reported back to the scheduler continuously from zun-compute running on the
compute node. To prevent the host CPU from being considered as available,
this option is used to reserve random pCPU(s) for the host.
Possible values:
* Any positive integer representing number of physical CPUs to reserve
  for the host.
"""),
]

allocation_ratio_opts = [
    cfg.FloatOpt('cpu_allocation_ratio',
                 default=None,
                 min=0.0,
                 help="""
Virtual CPU to physical CPU allocation ratio.
This option is used to influence the hosts selected by the Placement API. In
addition, the ``AggregateCoreFilter`` will fall back to this configuration
value if no per-aggregate setting is found.
.. note::
   If this option is set to something *other than* ``None`` or ``0.0``, the
   allocation ratio will be overwritten by the value of this option, otherwise,
   the allocation ratio will not change. Once set to a non-default value, it is
   not possible to "unset" the config to get back to the default behavior. If
   you want to reset back to the initial value, explicitly specify it to the
   value of ``initial_cpu_allocation_ratio``.
Possible values:
* Any valid positive integer or float value
Related options:
* ``initial_cpu_allocation_ratio``
"""),
    cfg.FloatOpt('ram_allocation_ratio',
                 default=None,
                 min=0.0,
                 help="""
Virtual RAM to physical RAM allocation ratio.
This option is used to influence the hosts selected by the Placement API. In
addition, the ``AggregateRamFilter`` will fall back to this configuration value
if no per-aggregate setting is found.
.. note::
   If this option is set to something *other than* ``None`` or ``0.0``, the
   allocation ratio will be overwritten by the value of this option, otherwise,
   the allocation ratio will not change. Once set to a non-default value, it is
   not possible to "unset" the config to get back to the default behavior. If
   you want to reset back to the initial value, explicitly specify it to the
   value of ``initial_ram_allocation_ratio``.
Possible values:
* Any valid positive integer or float value
Related options:
* ``initial_ram_allocation_ratio``
"""),
    cfg.FloatOpt('disk_allocation_ratio',
                 default=None,
                 min=0.0,
                 help="""
Virtual disk to physical disk allocation ratio.
This option is used to influence the hosts selected by the Placement API. In
addition, the ``AggregateDiskFilter`` will fall back to this configuration
value if no per-aggregate setting is found.
When configured, a ratio greater than 1.0 will result in over-subscription of
the available physical disk, which can be useful for more efficiently packing
containers created with images that do not use the entire virtual disk.
It can be set to a value between 0.0 and 1.0 in
order to preserve a percentage of the disk for uses other than containers.
.. note::
   If the value is set to ``>1``, we recommend keeping track of the free disk
   space, as the value approaching ``0`` may result in the incorrect
   functioning of instances using it at the moment.
.. note::
   If this option is set to something *other than* ``None`` or ``0.0``, the
   allocation ratio will be overwritten by the value of this option, otherwise,
   the allocation ratio will not change. Once set to a non-default value, it is
   not possible to "unset" the config to get back to the default behavior. If
   you want to reset back to the initial value, explicitly specify it to the
   value of ``initial_disk_allocation_ratio``.
Possible values:
* Any valid positive integer or float value
Related options:
* ``initial_disk_allocation_ratio``
"""),
    cfg.FloatOpt('initial_cpu_allocation_ratio',
                 default=16.0,
                 min=0.0,
                 help="""
Initial virtual CPU to physical CPU allocation ratio.
This is only used when initially creating the ``computes_nodes`` table record
for a given zun-compute service.
Related options:
* ``cpu_allocation_ratio``
"""),
    cfg.FloatOpt('initial_ram_allocation_ratio',
                 default=1.5,
                 min=0.0,
                 help="""
Initial virtual RAM to physical RAM allocation ratio.
This is only used when initially creating the ``computes_nodes`` table record
for a given zun-compute service.
Related options:
* ``ram_allocation_ratio``
"""),
    cfg.FloatOpt('initial_disk_allocation_ratio',
                 default=1.0,
                 min=0.0,
                 help="""
Initial virtual disk to physical disk allocation ratio.
This is only used when initially creating the ``computes_nodes`` table record
for a given zun-compute service.
Related options:
* ``disk_allocation_ratio``
""")
]

opt_group = cfg.OptGroup(
    name='compute', title='Options for the zun-compute service')

ALL_OPTS = (service_opts + db_opts + compute_opts + resource_tracker_opts +
            allocation_ratio_opts)


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(ALL_OPTS, opt_group)


def list_opts():
    return {opt_group: ALL_OPTS}
