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

ACTION = 'container:actions'
EVENT = 'container:action:events'

rules = [
    policy.DocumentedRuleDefault(
        name=ACTION,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List actions and show action details for a container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/container_actions/',
                'method': 'GET'
            },
            {
                'path': '/v1/containers/{container_ident}/container_actions/'
                        '{request_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=EVENT,
        check_str=base.RULE_ADMIN_API,
        description="Add events details in action details for a container.",
        operations=[
            {
                'path': '/v1/containers/{container_ident}/container_actions/'
                        '{request_id}',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
