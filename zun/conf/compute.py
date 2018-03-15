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
        default=True,
        help='restart the containers which are running'
             'before the host reboots.'),
    cfg.FloatOpt(
        'reserve_disk_for_image',
        default=0.2,
        help='reserve disk for docker images'),
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

opt_group = cfg.OptGroup(
    name='compute', title='Options for the zun-compute service')

ALL_OPTS = (service_opts + db_opts + compute_opts)


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(ALL_OPTS, opt_group)


def list_opts():
    return {opt_group: ALL_OPTS}
