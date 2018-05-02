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

query_param_enable = {
    'type': 'object',
    'properties': {
        'host': parameter_types.hostname,
        'binary': {
            'type': 'string', 'minLength': 1, 'maxLength': 255,
        },
    },
    'additionalProperties': False
}

query_param_disable = {
    'type': 'object',
    'properties': {
        'host': parameter_types.hostname,
        'binary': {
            'type': 'string', 'minLength': 1, 'maxLength': 255,
        },
        'disabled_reason': {
            'type': 'string', 'minLength': 1, 'maxLength': 255,
        },
    },
    'additionalProperties': False
}

query_param_force_down = {
    'type': 'object',
    'properties': {
        'host': parameter_types.hostname,
        'binary': {
            'type': 'string', 'minLength': 1, 'maxLength': 255,
        },
        'forced_down': parameter_types.boolean
    },
    'additionalProperties': False
}
