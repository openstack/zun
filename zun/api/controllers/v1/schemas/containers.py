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
    'auto_remove': parameter_types.auto_remove,
    'image_pull_policy': parameter_types.image_pull_policy,
    'labels': parameter_types.labels,
    'environment': parameter_types.environment,
    'restart_policy': parameter_types.restart_policy,
    'interactive': parameter_types.boolean,
    'image_driver': parameter_types.image_driver,
    'security_groups': parameter_types.security_groups,
    'hints': parameter_types.hints,
    'mounts': parameter_types.mounts,
    'nets': parameter_types.nets,
    'runtime': parameter_types.runtime,
    'hostname': parameter_types.hostname,
    'disk': parameter_types.positive_integer,
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
        'force': parameter_types.boolean_extended,
        'all_projects': parameter_types.boolean_extended,
        'stop': parameter_types.boolean_extended
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
        'stderr': parameter_types.boolean_extended,
        'timestamps': parameter_types.boolean_extended,
        'tail': parameter_types.str_and_int,
        'since': parameter_types.logs_since
    },
    'additionalProperties': False
}

query_param_top = {
    'type': 'object',
    'properties': {
        'ps_args': parameter_types.string_ps_args
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

query_param_execute_resize = {
    'type': 'object',
    'properties': {
        'exec_id': parameter_types.exec_id,
        'h': parameter_types.positive_integer,
        'w': parameter_types.positive_integer
    },
    'additionalProperties': False
}

query_param_signal = {
    'type': 'object',
    'properties': {
        'signal': parameter_types.signal
    },
    'additionalProperties': False
}

query_param_execute_command = {
    'type': 'object',
    'properties': {
        'run': parameter_types.boolean,
        'interactive': parameter_types.boolean,
        'command': parameter_types.exec_command,
    },
    'additionalProperties': False
}

query_param_commit = {
    'type': 'object',
    'properties': {
        'repository': parameter_types.string_ps_args,
        'tag': parameter_types.string_ps_args
    },
    'required': ['repository'],
    'additionalProperties': False
}
add_security_group = {
    'type': 'object',
    'properties': {
        'name': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 255
        }
    },
    'additionalProperties': False
}

remove_security_group = copy.deepcopy(add_security_group)

network_detach = {
    'type': 'object',
    'properties': {
        'network': {
            'type': 'string'
        }
    },
    'required': ['network'],
    'additionalProperties': False
}

network_attach = copy.deepcopy(network_detach)
