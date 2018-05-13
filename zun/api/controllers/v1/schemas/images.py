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

_image_properties = {
    'image_id': parameter_types.image_id,
    'repo': parameter_types.repo,
    'tag': parameter_types.tag,
    'size': parameter_types.size,
    'image_pull_policy': parameter_types.image_pull_policy,
    'host': parameter_types.image_host,
}

image_create = {
    'type': 'object',
    'properties': _image_properties,
    'required': ['repo', 'host'],
    'additionalProperties': False
}

query_param_search = {
    'type': 'object',
    'properties': {
        'image_driver': parameter_types.image_driver,
        'exact_match': parameter_types.boolean
    },
    'additionalProperties': False
}

query_param_delete = {
    'type': 'object',
    'properties': {
        'host': parameter_types.image_host,
    },
    'required': ['host'],
    'additionalProperties': False
}
