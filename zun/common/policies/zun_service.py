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

ZUN_SERVICE = 'zun-service:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=ZUN_SERVICE % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete a service.',
        operations=[
            {
                'path': '/v1/services',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ZUN_SERVICE % 'disable',
        check_str=base.RULE_ADMIN_API,
        description='Disable a service.',
        operations=[
            {
                'path': '/v1/services/disable',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ZUN_SERVICE % 'enable',
        check_str=base.RULE_ADMIN_API,
        description='Enable a service.',
        operations=[
            {
                'path': '/v1/services/enable',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ZUN_SERVICE % 'force_down',
        check_str=base.RULE_ADMIN_API,
        description='Forcibly shutdown a service.',
        operations=[
            {
                'path': '/v1/services/force_down',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=ZUN_SERVICE % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Show the status of a service.',
        operations=[
            {
                'path': '/v1/services',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
