# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from zun.api.controllers.v1.schemas import parameter_types

_network_properties = {
    'neutron_net_id': parameter_types.neutron_net_id,
    'name': parameter_types.network_name
}

network_create = {
    'type': 'object',
    'properties': _network_properties,
    'required': ['name'],
    'additionalProperties': False
}
