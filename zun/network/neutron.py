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

import ipaddress
import time

from neutron_lib import constants as n_const
from neutronclient.common import exceptions as n_exceptions
from neutronclient.neutron import v2_0 as neutronv20
from oslo_log import log as logging
from oslo_utils import uuidutils

from zun.common import clients
from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun.objects import fields as obj_fields
from zun.pci import manager as pci_manager
from zun.pci import utils as pci_utils
from zun.pci import whitelist as pci_whitelist


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class NeutronAPI(object):

    def __init__(self, context):
        self.context = context
        self.client = clients.OpenStackClients(self.context).neutron()
        self.admin_client = None
        self.pci_whitelist = pci_whitelist.Whitelist(
            CONF.pci.passthrough_whitelist)
        self.last_neutron_extension_sync = None
        self.extensions = {}

    def __getattr__(self, key):
        return getattr(self.client, key)

    def _get_admin_client(self):
        if self.admin_client is None:
            context = zun_context.get_admin_context()
            self.admin_client = clients.OpenStackClients(context).neutron()
        return self.admin_client

    def update_port(self, port, body=None, admin=False):
        if admin:
            client = self._get_admin_client()
        else:
            client = self.client
        return client.update_port(port, body)

    def create_port(self, body=None, admin=False):
        if admin:
            client = self._get_admin_client()
        else:
            client = self.client
        return client.create_port(body)

    def create_or_update_port(self, container, network_uuid,
                              requested_network, device_owner,
                              security_groups=None, set_binding_host=False):
        if requested_network.get('port'):
            neutron_port_id = requested_network.get('port')
            # update device_id in port
            port_req_body = {'port': {'device_id': container.uuid}}
            if set_binding_host:
                port_req_body['port']['device_owner'] = device_owner
                port_req_body['port'][consts.BINDING_HOST_ID] = container.host
            neutron_port = self.update_port(neutron_port_id, port_req_body,
                                            admin=True)

            # If there is pci_request_id, it should be a sriov port.
            # populate pci related info.
            pci_request_id = requested_network.get('pci_request_id')
            if pci_request_id:
                self._populate_neutron_extension_values(container,
                                                        pci_request_id,
                                                        port_req_body)
                self._populate_pci_mac_address(container,
                                               pci_request_id,
                                               port_req_body)
                # NOTE(hongbin): Use admin context here because non-admin
                # context might not be able to update some attributes
                # (i.e. binding:profile).
                neutron_port = self.update_port(neutron_port_id, port_req_body,
                                                admin=True)
        else:
            port_dict = {
                'network_id': network_uuid,
                'tenant_id': self.context.project_id,
                'device_id': container.uuid,
            }
            if set_binding_host:
                port_dict['device_owner'] = device_owner
                port_dict[consts.BINDING_HOST_ID] = container.host
            ip_addr = requested_network.get("fixed_ip")
            if ip_addr:
                port_dict['fixed_ips'] = [{'ip_address': ip_addr}]
            if security_groups is not None:
                port_dict['security_groups'] = security_groups
            neutron_port = self.create_port({'port': port_dict}, admin=True)

        neutron_port = neutron_port['port']
        preserve_on_delete = requested_network['preserve_on_delete']
        addresses = []
        for fixed_ip in neutron_port['fixed_ips']:
            ip_address = fixed_ip['ip_address']
            ip = ipaddress.ip_address(str(ip_address))
            if ip.version == 4:
                addresses.append({
                    'addr': ip_address,
                    'version': 4,
                    'port': neutron_port['id'],
                    'subnet_id': fixed_ip['subnet_id'],
                    'preserve_on_delete': preserve_on_delete
                })
            else:
                addresses.append({
                    'addr': ip_address,
                    'version': 6,
                    'port': neutron_port['id'],
                    'subnet_id': fixed_ip['subnet_id'],
                    'preserve_on_delete': preserve_on_delete
                })

        return addresses, neutron_port

    def delete_or_unbind_ports(self, ports, ports_to_delete):
        for port_id in ports:
            try:
                if port_id in ports_to_delete:
                    self.delete_port(port_id)
                else:
                    self._unbind_port(port_id)
            except n_exceptions.PortNotFoundClient:
                LOG.warning('Maybe your libnetwork distribution do not '
                            'have patch https://review.openstack.org/#/c/'
                            '441024/ or neutron tag extension does not '
                            'supported or not enabled.')

    def _unbind_port(self, port_id):
        port_req_body = {'port': {'device_id': '', 'device_owner': ''}}
        port_req_body['port'][consts.BINDING_HOST_ID] = None
        try:
            port = self.get_neutron_port(port_id)
        except exception.PortNotFound:
            LOG.debug('Unable to show port %s as it no longer '
                      'exists.', port_id)
            return
        except Exception:
            # NOTE: In case we can't retrieve the binding:profile assume
            # that they are empty
            LOG.exception("Unable to get binding:profile for port '%s'",
                          port_id)
            port_profile = {}
        else:
            port_profile = port.get(consts.BINDING_PROFILE, {})
        # NOTE: We're doing this to remove the binding information
        # for the physical device but don't want to overwrite the other
        # information in the binding profile.
        for profile_key in ('pci_vendor_info', 'pci_slot'):
            if profile_key in port_profile:
                del port_profile[profile_key]
        port_req_body['port'][consts.BINDING_PROFILE] = port_profile

        try:
            # Requires admin creds to set port bindings
            self.update_port(port_id, port_req_body, admin=True)
        except exception.PortNotFound:
            LOG.debug('Unable to unbind port %s as it no longer '
                      'exists.', port_id)
        except Exception:
            LOG.exception("Unable to clear device ID for port '%s'",
                          port_id)

    def _refresh_neutron_extensions_cache(self):
        """Refresh the neutron extensions cache when necessary."""
        if (not self.last_neutron_extension_sync or
            ((time.time() - self.last_neutron_extension_sync) >=
             CONF.neutron.extension_sync_interval)):
            extensions_list = self.neutron_api.list_extensions()['extensions']
            self.last_neutron_extension_sync = time.time()
            self.extensions.clear()
            self.extensions = {ext['name']: ext for ext in extensions_list}

    def _populate_neutron_extension_values(self, container, pci_request_id,
                                           port_req_body):
        self._refresh_neutron_extensions_cache()
        if "Port Binding" in self.extensions:
            self._populate_neutron_binding_profile(container, pci_request_id,
                                                   port_req_body)

    def _populate_neutron_binding_profile(self, container, pci_request_id,
                                          port_req_body):
        """Populate neutron binding:profile.

        Populate it with SR-IOV related information
        """
        if pci_request_id:
            pci_dev = pci_manager.get_container_pci_devs(
                container, pci_request_id).pop()
            profile = self._get_pci_device_profile(pci_dev)
            port_req_body['port'][consts.BINDING_PROFILE] = profile

    def _get_pci_device_profile(self, pci_dev):
        dev_spec = self.pci_whitelist.get_devspec(pci_dev)
        if dev_spec:
            return {'pci_vendor_info': "%s:%s" % (pci_dev.vendor_id,
                                                  pci_dev.product_id),
                    'pci_slot': pci_dev.address,
                    'physical_network':
                        dev_spec.get_tags().get('physical_network')}
        raise exception.PciDeviceNotFound(node_id=pci_dev.compute_node_uuid,
                                          address=pci_dev.address)

    def _populate_pci_mac_address(self, container, pci_request_id,
                                  port_req_body):
        """Add the updated MAC address value to the update_port request body.

        Currently this is done only for PF passthrough.
        """
        if pci_request_id is not None:
            pci_devs = pci_manager.get_container_pci_devs(
                container, pci_request_id)
            if len(pci_devs) != 1:
                # NOTE(ndipanov): We shouldn't ever get here since
                # InstancePCIRequest instances built from network requests
                # only ever index a single device, which needs to be
                # successfully claimed for this to be called as part of
                # allocate_networks method
                LOG.error("PCI request %(pci_request_id)s does not have a "
                          "unique device associated with it. Unable to "
                          "determine MAC address",
                          {'pci_request_id': pci_request_id},
                          container=container)
                return
            pci_dev = pci_devs[0]
            if pci_dev.dev_type == obj_fields.PciDeviceType.SRIOV_PF:
                try:
                    mac = pci_utils.get_mac_by_pci_address(pci_dev.address)
                except exception.PciDeviceNotFoundById as e:
                    LOG.error("Could not determine MAC address for %(addr)s, "
                              "error: %(e)s",
                              {"addr": pci_dev.address, "e": e},
                              container=container)
                else:
                    port_req_body['port']['mac_address'] = mac

    def find_resourceid_by_name_or_id(self, resource, name_or_id,
                                      project_id=None):
        return neutronv20.find_resourceid_by_name_or_id(
            self.client, resource, name_or_id, project_id)

    def get_available_network(self):
        search_opts = {'tenant_id': self.context.project_id, 'shared': False}
        # NOTE(kiennt): Pick shared network if no tenant network
        nets = self.list_networks(**search_opts).get('networks', []) or \
            self.list_networks(**{'shared': True}).get('networks', [])
        if not nets:
            raise exception.Conflict(_(
                "There is no neutron network available"))
        nets.sort(key=lambda x: x['created_at'])
        return nets[0]

    def get_neutron_network(self, network):
        if uuidutils.is_uuid_like(network):
            networks = self.list_networks(id=network)['networks']
        else:
            networks = self.list_networks(name=network)['networks']

        if len(networks) == 0:
            raise exception.NetworkNotFound(network=network)
        elif len(networks) > 1:
            raise exception.Conflict(_(
                'Multiple neutron networks exist with same name. '
                'Please use the uuid instead.'))

        network = networks[0]
        return network

    def get_neutron_port(self, port):
        if uuidutils.is_uuid_like(port):
            ports = self.list_ports(id=port)['ports']
        else:
            ports = self.list_ports(name=port)['ports']

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

        if port.get('status') in (n_const.PORT_STATUS_ACTIVE,
                                  n_const.PORT_STATUS_BUILD,
                                  n_const.PORT_STATUS_ERROR):
            raise exception.PortNotUsable(port=port['id'])

        # Make sure the port is usable
        binding_vif_type = port.get('binding:vif_type')
        if binding_vif_type == 'binding_failed':
            raise exception.PortBindingFailed(port=port['id'])

    def expose_ports(self, secgroup_id, ports):
        for port in ports:
            port, proto = port.split('/')
            secgroup_rule = {
                'security_group_id': secgroup_id,
                'direction': 'ingress',
                'port_range_min': port,
                'port_range_max': port,
                'protocol': proto,
                'remote_ip_prefix': '0.0.0.0/0',
            }

            try:
                self.create_security_group_rule({
                    'security_group_rule': secgroup_rule})
            except n_exceptions.NeutronClientException as ex:
                LOG.error("Error happened during creating a "
                          "Neutron security group "
                          "rule: %s", ex)
                self.delete_security_group(secgroup_id)
                raise exception.ZunException(_(
                    "Could not create required security group rules %s "
                    "for setting up exported port.") % secgroup_rule)
