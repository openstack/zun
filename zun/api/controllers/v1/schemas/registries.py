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


_registry_properties = {
    'name': parameter_types.registry_name,
    'domain': parameter_types.registry_domain,
    'username': parameter_types.registry_username,
    'password': parameter_types.registry_password,
}

registry_create = {
    'type': 'object',
    'properties': {
        'registry': {
            'type': 'object',
            'properties': _registry_properties,
            'additionalProperties': False,
            'required': ['domain'],
        },
    },
    'required': ['registry'],
    'additionalProperties': False,
}

_registry_update_properties = {
    'name': parameter_types.registry_name,
    'domain': parameter_types.registry_domain,
    'username': parameter_types.registry_username,
    'password': parameter_types.registry_password,
}

registry_update = {
    'type': 'object',
    'properties': {
        'registry': {
            'type': 'object',
            'properties': _registry_update_properties,
            'additionalProperties': False,
        },
    },
    'required': ['registry'],
    'additionalProperties': False,
}
