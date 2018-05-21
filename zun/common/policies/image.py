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

IMAGE = 'image:%s'

rules = [
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=IMAGE % 'pull',
        check_str=base.RULE_ADMIN_API,
        description='Pull an image.',
        operations=[
            {
                'path': '/v1/images',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=IMAGE % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Print a list of available images.',
        operations=[
            {
                'path': '/v1/images',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=IMAGE % 'get_one',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve the details of a specific image.',
        operations=[
            {
                'path': '/v1/images/{image_id}',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=IMAGE % 'search',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Search an image.',
        operations=[
            {
                'path': '/v1/images/{image_ident}/search',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=IMAGE % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete an image.',
        operations=[
            {
                'path': '/v1/images/{image_ident}',
                'method': 'DELETE'
            }
        ]
    )
]


def list_rules():
    return rules
