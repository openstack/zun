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

from oslo_log import log as logging
import pecan

from zun.api.controllers import base
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import network as schema
from zun.api.controllers.v1.views import network_view as view
from zun.api import utils as api_utils
from zun.api import validation
from zun.common import exception
from zun.common import policy
from zun import objects


LOG = logging.getLogger(__name__)


def _get_network(context, network_ident):
    networks = objects.Network.list(
        context,
        filters={'neutron_net_id': network_ident})
    if not networks:
        raise exception.NetworkNotFound(network=network_ident)

    return networks[0]


class NetworkCollection(collection.Collection):
    """API representation of a collection of network."""

    fields = {
        'network'
    }

    """A list containing network objects"""

    def __init__(self, **kwargs):
        super(NetworkCollection, self).__init__(**kwargs)
        self._type = 'network'

    @staticmethod
    def convert_with_links(rpc_network, limit, url=None,
                           expand=False, **kwargs):
        collection = NetworkCollection()
        collection.network = [view.format_network(url, p) for p in rpc_network]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class NetworkController(base.Controller):
    """Controller for Network"""

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.network_create)
    def post(self, **network_dict):
        """Create a new network.

        :param network_dict: a network within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, "network:create", action="network:create")
        new_network = pecan.request.compute_api.network_create(
            context, network_dict['neutron_net_id'])
        return view.format_network(pecan.request.host_url, new_network)

    @base.Controller.api_version("1.27")  # noqa
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def delete(self, network_ident, **kwargs):
        """Delete a network.

        :param network_ident: UUID of the network.
        """
        context = pecan.request.context
        policy.enforce(context, "network:delete", action="network:delete")
        context.all_projects = True
        network = _get_network(context, network_ident)
        compute_api = pecan.request.compute_api
        compute_api.network_delete(context, network)
        pecan.response.status = 204
