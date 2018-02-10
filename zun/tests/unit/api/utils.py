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


def zservice_get_data(**kwargs):
    """Simulate what the RPC layer will get from DB """
    faketime = datetime.datetime(2001, 1, 1, tzinfo=pytz.UTC)
    return {
        'binary': kwargs.get('binary', 'fake-binary'),
        'host': kwargs.get('host', 'fake-host'),
        'id': kwargs.get('id', 13),
        'report_count': kwargs.get('report_count', 13),
        'disabled': kwargs.get('disabled', False),
        'disabled_reason': kwargs.get('disabled_reason'),
        'forced_down': kwargs.get('forced_down', False),
        'last_seen_up': kwargs.get('last_seen_up', faketime),
        'created_at': kwargs.get('created_at', faketime),
        'updated_at': kwargs.get('updated_at', faketime),
        'availability_zone': kwargs.get('availability_zone', 'fake-zone'),
    }
