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

import datetime
import itertools

from zun.common import utils


_basic_keys = (
    'availability_zone',
    'binary',
    'created_at',
    'disabled',
    'disabled_reason',
    'forced_down',
    'host',
    'id',
    'last_seen_up',
    'report_count',
    'state',
    'updated_at',
)


def format_service(service):
    def transform(key, value):
        if key not in _basic_keys:
            return
        if isinstance(value, datetime.datetime):
            yield (key, utils.strtime(value))
        else:
            yield (key, value)

    return dict(
        itertools.chain.from_iterable(
            transform(k, v)for k, v in service.items()))
