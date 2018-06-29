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

CONTAINER = 'container:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a new container.',
        operations=[
            {
                'path': '/v1/containers',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'create:runtime',
        check_str=base.RULE_ADMIN_API,
        description='Create a new container with specified runtime.',
        operations=[
            {
                'path': '/v1/containers',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'delete_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Delete a container from all projects.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'delete_force',
        check_str=base.RULE_ADMIN_API,
        description='Forcibly delete a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_one',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve the details of a specific container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_one:host',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve the host field of containers.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'GET'
            },
            {
                'path': '/v1/containers',
                'method': 'GET'
            },
            {
                'path': '/v1/containers',
                'method': 'POST'
            },
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_one_all_projects',
        check_str=base.RULE_ADMIN_API,
        description=('Retrieve the details of a specific container from '
                     'all projects.'),
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_all',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve the details of all containers.',
        operations=[
            {
                'path': '/v1/containers',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve the details of all containers across projects.',
        operations=[
            {
                'path': '/v1/containers',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'update',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Update a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'start',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Start a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/start',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'stop',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Stop a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/stop',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'reboot',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Reboot a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/reboot',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'pause',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Pause a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/pause',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'unpause',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Unpause a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/unpause',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720924):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'logs',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get the log of a container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/logs',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720925):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'execute',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Execute command in a running container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/execute',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720926):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'execute_resize',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Resize the TTY used by an execute command.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/execute_resize',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720927):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'kill',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Kill a running container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/kill',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'rename',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Rename a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/rename',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720928):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'attach',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Attach to a running container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/attach',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'resize',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Resize a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/resize',
                'method': 'POST'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference (bug #1720929):
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'top',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Display the running processes inside the container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/top',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference, verify with someone from zun:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'get_archive',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get a tar archive of a path of container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/get_archive',
                'method': 'GET'
            }
        ]
    ),
    # FIXME(lbragstad): This API call isn't actually listed in zun's API
    # reference, verify with someone from zun:
    # https://developer.openstack.org/api-ref/application-container/
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'put_archive',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Put a tar archive to be extracted to a path of container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/put_archive',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'stats',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Display the statistics of a container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/stats',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'commit',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Commit a container',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/commit',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'add_security_group',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Add a security group to a specific container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/add_security_group',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'network_detach',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Detach a network from a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/network_detach',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'network_attach',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Attach a network from a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/network_attach',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'remove_security_group',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Remove security group from a specific container.',
        operations=[
            {
                'path': ('/v1/containers/'
                         '{container_ident}/remove_security_group'),
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'rebuild',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Rebuild a container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/rebuild',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CONTAINER % 'resize_container',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Resize an existing  container.',
        operations=[
            {
                'path': '/v1/containers/{container_ident}/resize_container',
                'method': 'POST'
            }
        ]
    ),
]


def list_rules():
    return rules
