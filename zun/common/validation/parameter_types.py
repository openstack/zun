# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import signal
import sys
import zun.conf

CONF = zun.conf.CONF

image_driver_list = [driver for driver in CONF.image_driver_list]

image_driver_list_with_none = image_driver_list + [None, 'None']

non_negative_integer = {
    'type': ['integer', 'string'],
    'pattern': '^[0-9]*$', 'minimum': 0
}

positive_integer = {
    'type': ['integer', 'string'],
    'pattern': '^[0-9]*$', 'minimum': 1
}

boolean_extended = {
    'type': ['boolean', 'string'],
    'enum': [True, 'True', 'TRUE', 'true', '1', 'ON', 'On', 'on',
             'YES', 'Yes', 'yes',
             False, 'False', 'FALSE', 'false', '0', 'OFF', 'Off', 'off',
             'NO', 'No', 'no'],
}

boolean = {
    'type': ['boolean', 'string'],
    'enum': [True, 'True', 'true', False, 'False', 'false'],
}

image_driver = {
    'type': ['string', 'null'],
    'enum': image_driver_list_with_none
}

container_name = {
    'type': ['string', 'null'],
    'minLength': 2,
    'maxLength': 255,
    'pattern': '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'
}

hex_uuid = {
    'type': 'string',
    'maxLength': 32,
    'minLength': 32,
    'pattern': '^[a-fA-F0-9]*$'
}

image_name = {
    'type': 'string',
    'minLength': 2,
    'maxLength': 255,
    'pattern': '[a-zA-Z0-9][a-zA-Z0-9_.-]'
}

command = {
    'type': ['string', 'null']
}

cpu = {
    'type': ['number', 'string', 'null'],
    'pattern': '^[0-9]*(\.([0-9]+))?$',
    'minLength': 1
}

# TODO(pksingh) Memory provided must be in MBs
# Will find another way if people dont find it useful.
memory = {
    'type': ['string', 'integer', 'null'],
    'minimum': 4,
    'pattern': '^[0-9]+$'
}

workdir = {
    'type': ['string', 'null']
}

image_pull_policy = {
    'type': ['string', 'null'],
    'enum': ['never', 'always', 'ifnotpresent', None]
}

labels = {
    'type': ['object', 'null']
}

environment = {
    'type': ['object', 'null']
}

image_id = {
    'type': ['string', 'null'],
    'minLength': 2,
    'maxLength': 255,
    'pattern': '[a-zA-Z0-9][a-zA-Z0-9_.-]'
}

repo = {
    'type': 'string',
    'minLength': 2,
    'maxLength': 255,
    'pattern': '[a-zA-Z0-9][a-zA-Z0-9_.-]'
}


tag = copy.deepcopy(image_id)

size = {
    'type': ['string', 'integer', 'null'],
    'pattern': '^[0-9]+[b|B|k|K|m|M|g|G]?$',
}

restart_policy = {
    'type': ['object', 'null'],
    "properties": {
        "Name": {"type": ["string"],
                 "enum": ['no', 'always', 'on-failure', 'unless-stopped']},
        "MaximumRetryCount": {"type": ['integer', 'string', 'null'],
                              "minimum": 0, 'pattern': '^[0-9]+$'},
    },
    "additionalProperties": False,
    "required": ['Name']
}

string_ps_args = {
    'type': ['string'],
    'pattern': '[a-zA-Z- ,+]*'
}

str_and_int = {
    'type': ['string', 'integer', 'null'],
}

logs_since = {
    'type': ['string', 'integer', 'null'],
    'pattern': '(^[0-9]*$)|\
([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{1,3})'
}

exec_id = {
    'type': 'string',
    'maxLength': 64,
    'minLength': 64,
    'pattern': '^[a-f0-9]*$'
}

SIGNALS = ['None']
if sys.version_info >= (3, 5, 0):
    signals = [n for n in signal.Signals]
    for s in signals:
        s = str(s).split('.')[1]
        SIGNALS.append(s)
        SIGNALS.append(s.replace('SIG', ''))
        SIGNALS.append(s.lower())
        SIGNALS.append(s.lower().replace('sig', ''))
        SIGNALS.append(str(int(getattr(signal, s))))
else:
    signals = [n for n in dir(signal) if n.startswith('SIG') and '_' not in n]
    for s in signals:
        SIGNALS.append(s)
        SIGNALS.append(s.replace('SIG', ''))
        SIGNALS.append(s.lower())
        SIGNALS.append(s.lower().replace('sig', ''))
        SIGNALS.append(str(getattr(signal, s)))

signal = {
    'type': ['string', 'null'],
    'enum': SIGNALS
}

exec_command = {
    'type': ['string'],
    'minLength': 1,
}
