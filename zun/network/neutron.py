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

from neutron_lib import constants as n_const
from oslo_utils import uuidutils

from zun.common import clients
from zun.common import exception
from zun.common.i18n import _


class NeutronAPI(object):

    def __init__(self, context):
        self.context = context
        self.neutron = clients.OpenStackClients(self.context).neutron()

    def get_available_network(self):
        search_opts = {'tenant_id': self.context.project_id, 'shared': False}
        nets = self.neutron.list_networks(**search_opts).get('networks', [])
        if not nets:
            raise exception.Conflict(_(
                "There is no neutron network available"))
        nets.sort(key=lambda x: x['created_at'])
        return nets[0]

    def get_neutron_port(self, port):
        if uuidutils.is_uuid_like(port):
            ports = self.neutron.list_ports(id=port)['ports']
        else:
            ports = self.neutron.list_ports(name=port)['ports']

        if len(ports) == 0:
            raise exception.PortNotFound(port=port)
        elif len(ports) > 1:
            raise exception.Conflict(_(
                'Multiple neutron ports exist with same name. '
                'Please use the uuid instead.'))

        port = ports[0]
        return port

    def ensure_neutron_port_usable(self, port, project_id=None):
        if project_id is None:
            project_id = self.context.project_id

        # Make sure the container has access to the port.
        if port['tenant_id'] != project_id:
            raise exception.PortNotUsable(port=port['id'])

        # Make sure the port isn't already attached to another
        # container or Nova instance.
        if port.get('device_id'):
            raise exception.PortInUse(port=port['id'])

        if port.get('status') == (n_const.PORT_STATUS_ACTIVE,
                                  n_const.PORT_STATUS_BUILD,
                                  n_const.PORT_STATUS_ERROR):
            raise exception.PortNotUsable(port=port['id'])

        # Make sure the port is usable
        binding_vif_type = port.get('binding:vif_type')
        if binding_vif_type == 'binding_failed':
            raise exception.PortBindingFailed(port=port['id'])
