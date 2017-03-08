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
"""
Utils for testing the API service.
"""
import datetime

import pytz


def zservice_get_data(**kw):
    """Simulate what the RPC layer will get from DB """
    faketime = datetime.datetime(2001, 1, 1, tzinfo=pytz.UTC)
    return {
        'binary': kw.get('binary', 'fake-binary'),
        'host': kw.get('host', 'fake-host'),
        'id': kw.get('id', 13),
        'report_count': kw.get('report_count', 13),
        'disabled': kw.get('disabled', False),
        'disabled_reason': kw.get('disabled_reason'),
        'forced_down': kw.get('forced_down', False),
        'last_seen_up': kw.get('last_seen_up', faketime),
        'created_at': kw.get('created_at', faketime),
        'updated_at': kw.get('updated_at', faketime),
    }
