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

QUOTA_CLASS = 'quota_class:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=QUOTA_CLASS % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update quotas for specific quota class',
        operations=[
            {
                'path': '/v1/quota_classes/{quota_class_name}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA_CLASS % 'get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List quotas for specific quota class',
        operations=[
            {
                'path': '/v1/quota_classes/{quota_class_name}',
                'method': 'GET'
            }
        ]
    ),
]


def list_rules():
    return rules
