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

QUOTA = 'quota:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=QUOTA % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update quotas for a project',
        operations=[
            {
                'path': '/v1/quotas/{project_id}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete quotas for a project',
        operations=[
            {
                'path': '/v1/quotas/{project_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get quotas for a project',
        operations=[
            {
                'path': '/v1/quotas/{project_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'get_default',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get default quotas for a project',
        operations=[
            {
                'path': '/v1/quotas/{project_id}/defaults',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
