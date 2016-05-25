# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

import higgins.api.app
import higgins.common.keystone
import higgins.common.service
import higgins.conductor.config


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             higgins.common.service.service_opts,
         )),
        ('api', higgins.api.app.API_SERVICE_OPTS),
        ('conductor', higgins.conductor.config.SERVICE_OPTS),
        ('keystone_auth', higgins.common.keystone.keystone_auth_opts),
    ]
