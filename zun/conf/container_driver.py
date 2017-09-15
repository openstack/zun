# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

driver_opts = [
    cfg.StrOpt('container_driver',
               default='docker.driver.DockerDriver',
               help="""Defines which driver to use for controlling container.
Possible values:

* ``docker.driver.DockerDriver``

Services which consume this:

* ``zun-compute``

Interdependencies to other options:

* None
"""),
    cfg.IntOpt('default_sleep_time', default=1,
               help='Time to sleep (in seconds) during waiting for an event.'),
    cfg.IntOpt('default_timeout', default=60 * 10,
               help='Maximum time (in seconds) to wait for an event.'),
    cfg.StrOpt('floating_cpu_set',
               default="",
               help='Define the cpusets to be excluded from pinning'),
    cfg.BoolOpt('use_sandbox',
                default=False,
                help="""Whether to use infra container. If set to True,
Zun will create an infra container that serves as a placeholder of a few
Linux namespaces (i.e. network namespace). Then, one or multiple containers
could join the namespaces of the infra container thus sharing resources inside
the sandbox (i.e. the network interface). This is typically used to group
a set of high-coupled containers into a unit. If set to False, infra container
won't be created.
"""),
    cfg.StrOpt('container_runtime', default='runc',
               help="""Define the runtime to create container with. Default value
in Zun is ``runc``.""")
]


ALL_OPTS = (driver_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
