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

CAPSULE = 'capsule:%s'

rules = [
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a capsule',
        operations=[
            {
                'path': '/v1/capsules/',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a capsule',
        operations=[
            {
                'path': '/v1/capsules/{capsule_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'delete_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Delete a container in any project.',
        operations=[
            {
                'path': '/v1/capsules/{capsule_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve the details of a capsule.',
        operations=[
            {
                'path': '/v1/capsules/{capsule_ident}',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'get_one_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve the details of a capsule in any project.',
        operations=[
            {
                'path': '/v1/capsules/{capsule_ident}',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'get_all',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List all capsules.',
        operations=[
            {
                'path': '/v1/capsules/',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CAPSULE % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='List all capsules across projects.',
        operations=[
            {
                'path': '/v1/capsules/',
                'method': 'GET'
            }
        ]
    ),
]


def list_rules():
    return rules
