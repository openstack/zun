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

boolean = {
    'type': 'boolean',
    'enum': [True, False]
}

container_name = {
    'type': 'string',
    'minLength': 2,
    'maxLength': 255,
    'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'
}

hex_uuid = {
    'type': 'string',
    'maxLength': 32,
    'minLength': 32,
    'pattern': '^[a-fA-F0-9]*$'
}

image_name = {
    'type': 'string',
    'minLength': 2,
    'maxLength': 255,
    'pattern': '[a-zA-Z0-9][a-zA-Z0-9_.-]'
}

command = {
    'type': 'string'
}

cpu = {
    'type': 'number'
}

memory = {
    'type': ['string', 'integer'],
    'pattern': '^[0-9]+[k|K|m|M|g|G]?$',
    'minimum': 4194304
}

workdir = {
    'type': 'string'
}

hostname = {
    'type': 'string',
    'minLength': 0,
    'maxLength': 255
}

image_pull_policy = {
    'type': 'string',
    'enum': ['never', 'always', 'ifnotpresent']
}
