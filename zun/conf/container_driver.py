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
""")
]


ALL_OPTS = (driver_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
