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


neutron_group = cfg.OptGroup(name='neutron', title='Options for neutron')

neutron_opts = [
    cfg.StrOpt('ovs_bridge',
               default='br-int',
               help="""
Default name for the Open vSwitch integration bridge.

Specifies the name of an integration bridge interface used by OpenvSwitch.
This option is only used if Neutron does not specify the OVS bridge name in
port binding responses.
"""),
]

ALL_OPTS = (neutron_opts)


def register_opts(conf):
    conf.register_group(neutron_group)
    conf.register_opts(ALL_OPTS, neutron_group)


def list_opts():
    return {neutron_group: ALL_OPTS}
