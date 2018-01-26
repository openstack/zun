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


_basic_keys = (
    'id',
    'uuid',
    'user_id',
    'project_id',
    'created_at',
    'updated_at',
    'addresses',
    'volumes_info',
    'status',
    'restart_policy',
    'meta_name',
    'meta_labels',
    'containers_uuids',
    'capsule_version',
    'memory',
    'cpu'
)


def format_capsule(url, capsule):
    def transform(key, value):
        if key not in _basic_keys:
            return
        if key == 'uuid':
            yield ('uuid', value)
            yield ('links', [link.make_link(
                'self', url, 'capsules', value),
                link.make_link(
                    'bookmark', url,
                    'capsules', value,
                    bookmark=True)])
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in capsule.as_dict().items()))
