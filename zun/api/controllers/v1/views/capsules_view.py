#    Copyright 2017 ARM Holdings.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import itertools

from zun.api.controllers import link
from zun.api.controllers.v1.views import containers_view
from zun.common.policies import capsule as policies


_basic_keys = (
    'uuid',
    'user_id',
    'project_id',
    'created_at',
    'updated_at',
    'addresses',
    'status',
    'status_reason',
    'restart_policy',
    'name',
    'labels',
    'memory',
    'cpu',
    'init_containers',
    'containers',
    'host',
)


def format_capsule(url, capsule, context, legacy_api_version=False):
    def transform(key, value):
        if key not in _basic_keys:
            return
        # strip the key if it is not allowed by policy
        policy_action = policies.CAPSULE % ('get:%s' % key)
        if not context.can(policy_action, fatal=False, might_not_exist=True):
            return
        if key == 'uuid':
            yield ('uuid', value)
            yield ('links', [link.make_link(
                'self', url, 'capsules', value),
                link.make_link(
                    'bookmark', url,
                    'capsules', value,
                    bookmark=True)])
            if legacy_api_version:
                yield('volumes_info', {})
                yield('containers_uuids', [])
                yield('init_containers_uuids', [])
                yield('capsule_version', '')
        elif key == 'init_containers':
            containers = []
            for c in capsule.init_containers:
                container = containers_view.format_container(
                    context, None, c)
                containers.append(container)
            yield ('init_containers', containers)
        elif key == 'containers':
            containers = []
            for c in capsule.containers:
                container = containers_view.format_container(
                    context, None, c)
                containers.append(container)
            yield ('containers', containers)
        elif key == 'name':
            if legacy_api_version:
                yield('meta_name', value)
            else:
                yield(key, value)
        elif key == 'labels':
            if legacy_api_version:
                yield('meta_labels', value)
            else:
                yield(key, value)
        elif key == 'restart_policy':
            if legacy_api_version:
                if 'Name' in value:
                    yield(key, value['Name'])
            else:
                yield(key, value)
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in capsule.as_dict().items()))
