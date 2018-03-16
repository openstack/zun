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

"""Possible actions on an container.

Action should probably match a user intention at the API level. Because they
can be user visible that should help to avoid confusion. For that reason they
tent to maintain the casing sent to the API.

Maintaining a list of actions here should protect against inconsistencies when
they are used.
"""

CREATE = 'create'
DELETE = 'delete'
REBOOT = 'reboot'
REBUILD = 'rebuild'
STOP = 'stop'
START = 'start'
PAUSE = 'pause'
UNPAUSE = 'unpause'
EXEC_CMD = 'exec_cmd'
KILL = 'kill'
UPDATE = 'update'
CONTAINER_ATTACH = 'container_attach'
RESIZE = 'resize'
ADD_SECURITY_GROUP = 'add_security_group'
REMOVE_SECURITY_GROUP = 'remove_security_group'
PUT_ARCHIVE = 'put_archive'
COMMIT = 'commit'
NETWORK_DETACH = 'network_detach'
NETWORK_ATTACH = 'network_attach'
