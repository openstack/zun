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
from oslo_utils import netutils


netconf_opts = [
    cfg.StrOpt("my_ip",
               default=netutils.get_my_ipv4(),
               help="""
The IP address which the host is using to connect to the management network.

Possible values:

* String with valid IP address. Default is IPv4 address of this host.

Related options:

* my_block_storage_ip
"""),
    cfg.StrOpt("my_block_storage_ip",
               default="$my_ip",
               help="""
The IP address which is used to connect to the block storage network.

Possible values:

* String with valid IP address. Default is IP address of this host.

Related options:

* my_ip - if my_block_storage_ip is not set, then my_ip value is used.
"""),
]


ALL_OPTS = (netconf_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
