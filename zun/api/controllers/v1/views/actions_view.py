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


_action_keys = (
    'action',
    'container_uuid',
    'finish_time',
    'message',
    'project_id',
    'request_id',
    'start_time',
    'user_id',
)


_action_event_keys = (
    'event',
    'finish_time',
    'result',
    'start_time',
    'traceback',
)


def format_action(action):
    def transform(key, value):
        if key not in _action_keys:
            return

        if isinstance(value, datetime.datetime):
            yield (key, utils.strtime(value))
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in action.as_dict().items()))


def format_event(event, show_traceback=False):
    def transform(key, value):
        if key not in _action_event_keys:
            return

        if isinstance(value, datetime.datetime):
            yield (key, utils.strtime(value))
        else:
            if key == 'traceback' and not show_traceback:
                # By default, non-admins are not allowed to see traceback
                # details.
                yield (key, None)
            else:
                yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in event.as_dict().items()))
