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

import zun.api.app
import zun.common.keystone
import zun.common.rpc_service
import zun.common.service
import zun.conductor.config


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             zun.common.rpc_service.periodic_opts,
             zun.common.service.service_opts,
         )),
        ('api', zun.api.app.API_SERVICE_OPTS),
        ('conductor', zun.conductor.config.SERVICE_OPTS),
        ('keystone_auth', zun.common.keystone.keystone_auth_opts),
    ]
