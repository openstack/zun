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

NETWORK = 'network:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=NETWORK % 'attach_external_network',
        check_str=base.ROLE_ADMIN,
        description='Attach an unshared external network to a container',
        operations=[
            {
                'path': '/v1/containers',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NETWORK % 'create',
        check_str=base.ROLE_ADMIN,
        description='Create a network',
        operations=[
            {
                'path': '/v1/networks',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules
