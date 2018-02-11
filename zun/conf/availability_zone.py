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

availability_zone_opts = [
    cfg.StrOpt('default_availability_zone',
               default='nova',
               help="""
Default availability zone for compute services.

This option determines the default availability zone for 'zun-compute'
services.

Possible values:

* Any string representing an existing availability zone name.
"""),
    cfg.StrOpt('default_schedule_zone',
               help="""
Default availability zone for containers.

This option determines the default availability zone for containers, which will
be used when a user does not specify one when creating a container. The
container(s) will be bound to this availability zone for their lifetime.

Possible values:

* Any string representing an existing availability zone name.
* None, which means that the container can move from one availability zone to
  another during its lifetime if it is moved from one compute node to another.
"""),
]


def register_opts(conf):
    conf.register_opts(availability_zone_opts)


def list_opts():
    return {'DEFAULT': availability_zone_opts}
