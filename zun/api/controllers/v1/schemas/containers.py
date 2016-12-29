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

import copy

from zun.common.validation import parameter_types

_container_properties = {
    'name': parameter_types.container_name,
    'image': parameter_types.image_name,
    'command': parameter_types.command,
    'cpu': parameter_types.cpu,
    'memory': parameter_types.memory,
    'workdir': parameter_types.workdir,
    'image_pull_policy': parameter_types.image_pull_policy,
    'labels': parameter_types.labels,
    'environment': parameter_types.environment,
    'restart_policy': parameter_types.restart_policy,
    'tty': parameter_types.boolean,
    'stdin_open': parameter_types.boolean,
    'image_driver': parameter_types.image_driver
}

container_create = {
    'type': 'object',
    'properties': _container_properties,
    'required': ['image'],
    'additionalProperties': False
}

query_param_rename = {
    'type': 'object',
    'properties': {
        'name': parameter_types.container_name
    },
    'additionalProperties': False
}

query_param_create = {
    'type': 'object',
    'properties': {
        'run': parameter_types.boolean_extended
    },
    'additionalProperties': False
}

_container_update_properties = {
    'cpu': parameter_types.cpu,
    'memory': parameter_types.memory,
}

container_update = {
    'type': 'object',
    'properties': _container_update_properties,
    'additionalProperties': False
}

query_param_delete = {
    'type': 'object',
    'properties': {
        'force': parameter_types.boolean_extended
    },
    'additionalProperties': False
}

query_param_reboot = {
    'type': 'object',
    'properties': {
        'timeout': parameter_types.non_negative_integer
    },
    'additionalProperties': False
}

query_param_logs = {
    'type': 'object',
    'properties': {
        'stdout': parameter_types.boolean_extended,
        'stderr': parameter_types.boolean_extended
    },
    'additionalProperties': False
}

query_param_stop = copy.deepcopy(query_param_reboot)

query_param_resize = {
    'type': 'object',
    'properties': {
        'h': parameter_types.positive_integer,
        'w': parameter_types.positive_integer
    },
    'additionalProperties': False
}
