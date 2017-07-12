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

from zun.common import clients
from zun.common import exception
from zun.common.i18n import _


class NeutronAPI(object):

    def __init__(self, context):
        self.context = context

    def get_available_network(self):
        neutron = clients.OpenStackClients(self.context).neutron()
        search_opts = {'tenant_id': self.context.project_id, 'shared': False}
        nets = neutron.list_networks(**search_opts).get('networks', [])
        if not nets:
            raise exception.Conflict(_(
                "There is no neutron network available"))
        nets.sort(key=lambda x: x['created_at'])
        return nets[0]
