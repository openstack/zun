# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

from zun.common.policies import base


REGISTRY = 'registry:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a new registry.',
        operations=[
            {
                'path': '/v1/registries',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a registry.',
        operations=[
            {
                'path': '/v1/registries/{registry_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'get_one',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve the details of a specific registry.',
        operations=[
            {
                'path': '/v1/registries/{registry_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'get_all',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve the details of all registries.',
        operations=[
            {
                'path': '/v1/registries',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve the details of all registries across projects.',
        operations=[
            {
                'path': '/v1/registries',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=REGISTRY % 'update',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Update a registry.',
        operations=[
            {
                'path': '/v1/registries/{registry_ident}',
                'method': 'PATCH'
            }
        ]
    ),
]


def list_rules():
    return rules
