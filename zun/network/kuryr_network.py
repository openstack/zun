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
import six
import sys
import time

from neutronclient.common import exceptions
from oslo_log import log as logging
from oslo_utils import excutils

from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun.network import network
from zun.network import neutron
from zun import objects
from zun.objects import fields as obj_fields
from zun.pci import manager as pci_manager
from zun.pci import utils as pci_utils
from zun.pci import whitelist as pci_whitelist

CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)

BINDING_PROFILE = 'binding:profile'
BINDING_HOST_ID = 'binding:host_id'
DEVICE_OWNER = 'compute:kuryr'


class KuryrNetwork(network.Network):
    def init(self, context, docker_api):
        self.docker = docker_api
        self.neutron_api = neutron.NeutronAPI(context)
        self.context = context
        self.pci_whitelist = pci_whitelist.Whitelist(
            CONF.pci.passthrough_whitelist)
        self.last_neutron_extension_sync = None
        self.extensions = {}

    def create_network(self, name, neutron_net_id):
        """Create a docker network with Kuryr driver.

        The docker network to be created will be based on the specified
        neutron net. It is assumed that the neutron net will have one
        or two subnets. If there are two subnets, it must be a ipv4
        subnet and a ipv6 subnet and containers created from this network
        will have both ipv4 and ipv6 addresses.

        What this method does is finding the subnets under the specified
        neutron net, retrieving the cidr, gateway of each
        subnet, and compile the list of parameters for docker.create_network.
        """
        # find a v4 and/or v6 subnet of the network
        shared = \
            self.neutron_api.get_neutron_network(neutron_net_id)[
                'shared']
        subnets = self.neutron_api.list_subnets(network_id=neutron_net_id)
        subnets = subnets.get('subnets', [])
        v4_subnet = self._get_subnet(subnets, ip_version=4)
        v6_subnet = self._get_subnet(subnets, ip_version=6)
        if not v4_subnet and not v6_subnet:
            raise exception.ZunException(_(
                "The Neutron network %s has no subnet") % neutron_net_id)

        # IPAM driver specific options
        ipam_options = {
            "Driver": CONF.network.driver_name,
            "Options": {
                'neutron.net.shared': str(shared)
            },
            "Config": []
        }

        # Driver specific options
        options = {
            'neutron.net.uuid': neutron_net_id,
            'neutron.net.shared': str(shared)
        }

        if v4_subnet:
            ipam_options['Options']['neutron.subnet.uuid'] = \
                v4_subnet.get('id')
            ipam_options["Config"].append({
                "Subnet": v4_subnet['cidr'],
                "Gateway": v4_subnet['gateway_ip']
            })

            options['neutron.subnet.uuid'] = v4_subnet.get('id')
        if v6_subnet:
            ipam_options['Options']['neutron.subnet.v6.uuid'] = \
                v6_subnet.get('id')
            ipam_options["Config"].append({
                "Subnet": v6_subnet['cidr'],
                "Gateway": v6_subnet['gateway_ip']
            })

            options['neutron.subnet.v6.uuid'] = v6_subnet.get('id')

        network_dict = {}
        network_dict['project_id'] = self.context.project_id
        network_dict['user_id'] = self.context.user_id
        network_dict['name'] = name
        network_dict['neutron_net_id'] = neutron_net_id
        network = objects.Network(self.context, **network_dict)

        for attempt in (1, 2, 3):
            LOG.debug("Attempt (%s) to create network: %s", attempt, network)
            created_network = self._create_network_attempt(
                network, options, ipam_options)
            if created_network:
                return created_network
            time.sleep(1)

        raise exception.ZunException(_(
            "Cannot create docker network after several attempts %s"))

    def _create_network_attempt(self, network, options, ipam_options):
        # The DB model has unique constraint on 'neutron_net_id' field
        # which will guarantee only one request can create the network in here
        # (and call docker.create_network later) if there are concurrent
        # requests on creating networks for the same neutron net.
        try:
            network.create(self.context)
        except exception.NetworkAlreadyExists as e:
            if e.field != 'neutron_net_id':
                raise

            networks = objects.Network.list(
                self.context,
                filters={'neutron_net_id': network.neutron_net_id})
            LOG.debug("network objects with 'neutron_net_id' as '%(net_id)s': "
                      "%(networks)s",
                      {"net_id": network.neutron_net_id,
                       "networks": networks})
            docker_networks = self.list_networks(names=[network.name])
            LOG.debug("docker networks with name matching '%(name)s': "
                      "%(networks)s",
                      {"name": network.name,
                       "networks": docker_networks})
            if (networks and networks[0].network_id and
                    docker_networks and
                    networks[0].network_id == docker_networks[0]['Id']):
                LOG.debug("Network (%s) has already been created in docker",
                          network.name)
                return networks[0]
            else:
                # Probably, there are concurrent requests on creating the
                # network but the network is yet created in Docker.
                # We return False and let the caller retry.
                return False

        LOG.debug("Calling docker.create_network to create network %s, "
                  "ipam_options %s, options %s",
                  network.name, ipam_options, options)
        enable_ipv6 = bool(options.get('neutron.subnet.v6.uuid'))
        try:
            docker_network = self.docker.create_network(
                name=network.name,
                driver=CONF.network.driver_name,
                enable_ipv6=enable_ipv6,
                options=options,
                ipam=ipam_options)
        except Exception:
            with excutils.save_and_reraise_exception():
                network.destroy()

        network.network_id = docker_network['Id']
        network.save()
        return network

    def _get_subnet(self, subnets, ip_version):
        subnets = [s for s in subnets if s['ip_version'] == ip_version]
        if len(subnets) == 0:
            return None
        elif len(subnets) == 1:
            return subnets[0]
        else:
            raise exception.ZunException(_(
                "Multiple Neutron subnets exist with ip version %s") %
                ip_version)

    def remove_network(self, network):
        self.docker.remove_network(network.name)
        network.destroy()

    def inspect_network(self, network_name):
        return self.docker.inspect_network(network_name)

    def list_networks(self, **kwargs):
        return self.docker.networks(**kwargs)

    def create_or_update_port(self, container, network_name,
                              requested_network, security_groups=None,
                              set_binding_host=False):
        if requested_network.get('port'):
            neutron_port_id = requested_network.get('port')
            neutron_port = self.neutron_api.get_neutron_port(neutron_port_id)
            # update device_id in port
            port_req_body = {'port': {'device_id': container.uuid}}
            if set_binding_host:
                port_req_body['port']['device_owner'] = DEVICE_OWNER
                port_req_body['port'][BINDING_HOST_ID] = container.host
            self.neutron_api.update_port(neutron_port_id, port_req_body,
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
                self.neutron_api.update_port(neutron_port_id, port_req_body,
                                             admin=True)
        else:
            network = self.inspect_network(network_name)
            neutron_net_id = network['Options']['neutron.net.uuid']
            port_dict = {
                'network_id': neutron_net_id,
                'tenant_id': self.context.project_id,
                'device_id': container.uuid,
            }
            if set_binding_host:
                port_dict['device_owner'] = DEVICE_OWNER
                port_dict[BINDING_HOST_ID] = container.host
            ip_addr = requested_network.get("fixed_ip")
            if ip_addr:
                port_dict['fixed_ips'] = [{'ip_address': ip_addr}]
            if security_groups is not None:
                port_dict['security_groups'] = security_groups
            neutron_port = self.neutron_api.create_port({'port': port_dict},
                                                        admin=True)
            neutron_port = neutron_port['port']

        preserve_on_delete = requested_network['preserve_on_delete']
        addresses = []
        for fixed_ip in neutron_port['fixed_ips']:
            ip_address = fixed_ip['ip_address']
            ip = ipaddress.ip_address(six.text_type(ip_address))
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

    def connect_container_to_network(self, container, network_name,
                                     requested_network, security_groups=None):
        """Connect container to the network

        This method will create a neutron port, retrieve the ip address(es)
        of the port, and pass them to docker.connect_container_to_network.
        """
        container_id = container.container_id

        addresses, original_port = self.create_or_update_port(
            container, network_name, requested_network, security_groups)

        ipv4_address = None
        ipv6_address = None
        for address in addresses:
            if address['version'] == 4:
                ipv4_address = address['addr']
            if address['version'] == 6:
                ipv6_address = address['addr']

        kwargs = {}
        if ipv4_address:
            kwargs['ipv4_address'] = ipv4_address
        if ipv6_address:
            kwargs['ipv6_address'] = ipv6_address
        try:
            self.docker.connect_container_to_network(
                container_id, network_name, **kwargs)
        except exception.DockerError:
            with excutils.save_and_reraise_exception():
                self.do_port_cleanup(addresses, original_port)
        return addresses

    def do_port_cleanup(self, addresses, port):
        preserve_flag = addresses[0].get('preserve_on_delete')
        port_id = port.get('id')
        if preserve_flag:
            port_req_body = {'port': {'device_id': '', 'device_owner': ''}}
            port_req_body['port'][BINDING_HOST_ID] = None
            port_req_body['port']['mac_address'] = port.get('mac_address')
            port_req_body['port'][BINDING_PROFILE] = \
                port.get(BINDING_PROFILE, {})

            try:
                # Requires admin creds to set port bindings
                self.neutron_api.update_port(port_id, port_req_body,
                                             admin=True)
            except exception.PortNotFound:
                LOG.debug('Unable to unbind port %s as it no longer '
                          'exists.', port_id)
            except Exception:
                LOG.exception("Unable to clear device ID for port '%s'",
                              port_id)
        else:
            try:
                self.neutron_api.delete_port(port_id)
            except exception.PortNotFound:
                LOG.debug('Unable to delete port %s as it no longer '
                          'exists.', port_id)

    def disconnect_container_from_network(self, container, network_name,
                                          neutron_network_id=None):
        container_id = container.container_id

        addrs_list = []
        if container.addresses and neutron_network_id:
            addrs_list = container.addresses.get(neutron_network_id, [])

        self._disconnect_container_from_network(container_id, network_name,
                                                addrs_list)

    def _disconnect_container_from_network(self, container_id, network_name,
                                           addrs_list):
        neutron_ports = set()
        all_ports = set()
        for addr in addrs_list:
            all_ports.add(addr['port'])
            if not addr['preserve_on_delete']:
                port_id = addr['port']
                neutron_ports.add(port_id)

        try:
            if container_id:
                self.docker.disconnect_container_from_network(container_id,
                                                              network_name)
        finally:
            for port_id in all_ports:
                try:
                    if port_id in neutron_ports:
                        self.neutron_api.delete_port(port_id)
                    else:
                        self._unbind_port(port_id)
                except exceptions.PortNotFoundClient:
                    LOG.warning('Maybe your libnetwork distribution do not '
                                'have patch https://review.openstack.org/#/c/'
                                '441024/ or neutron tag extension does not '
                                'supported or not enabled.')

    def _unbind_port(self, port_id):
        port_req_body = {'port': {'device_id': '', 'device_owner': ''}}
        port_req_body['port'][BINDING_HOST_ID] = None
        try:
            port = self.neutron_api.get_neutron_port(port_id)
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
            port_profile = port.get(BINDING_PROFILE, {})
        # NOTE: We're doing this to remove the binding information
        # for the physical device but don't want to overwrite the other
        # information in the binding profile.
        for profile_key in ('pci_vendor_info', 'pci_slot'):
            if profile_key in port_profile:
                del port_profile[profile_key]
        port_req_body['port'][BINDING_PROFILE] = port_profile

        try:
            # Requires admin creds to set port bindings
            self.neutron_api.update_port(port_id, port_req_body,
                                         admin=True)
        except exception.PortNotFound:
            LOG.debug('Unable to unbind port %s as it no longer '
                      'exists.', port_id)
        except Exception:
            LOG.exception("Unable to clear device ID for port '%s'",
                          port_id)

    def add_security_groups_to_ports(self, container, security_group_ids):
        port_ids = set()
        for addrs_list in container.addresses.values():
            for addr in addrs_list:
                port_id = addr['port']
                port_ids.add(port_id)

        search_opts = {'tenant_id': self.context.project_id}
        neutron_ports = self.neutron_api.list_ports(
            **search_opts).get('ports', [])
        neutron_ports = [p for p in neutron_ports if p['id'] in port_ids]
        for port in neutron_ports:
            if 'security_groups' not in port:
                port['security_groups'] = []
            port['security_groups'].extend(security_group_ids)
            updated_port = {'security_groups': port['security_groups']}
            try:
                LOG.info("Adding security group %(security_group_ids)s "
                         "to port %(port_id)s",
                         {'security_group_ids': security_group_ids,
                          'port_id': port['id']})
                self.neutron_api.update_port(port['id'],
                                             {'port': updated_port},
                                             admin=True)
            except exceptions.NeutronClientException as e:
                exc_info = sys.exc_info()
                if e.status_code == 400:
                    raise exception.SecurityGroupCannotBeApplied(
                        six.text_type(e))
                else:
                    six.reraise(*exc_info)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Neutron Error:")

    def remove_security_groups_from_ports(self, container, security_group_ids):
        port_ids = set()
        for addrs_list in container.addresses.values():
            for addr in addrs_list:
                port_id = addr['port']
                port_ids.add(port_id)

        search_opts = {'tenant_id': self.context.project_id}
        neutron_ports = self.neutron_api.list_ports(
            **search_opts).get('ports', [])
        neutron_ports = [p for p in neutron_ports if p['id'] in port_ids]
        for port in neutron_ports:
            port['security_groups'].remove(security_group_ids[0])
            updated_port = {'security_groups': port['security_groups']}
            try:
                LOG.info("Removing security group %(security_group_ids)s "
                         "from port %(port_id)s",
                         {'security_group_ids': security_group_ids,
                          'port_id': port['id']})
                self.neutron_api.update_port(port['id'],
                                             {'port': updated_port},
                                             admin=True)
            except exceptions.NeutronClientException as e:
                exc_info = sys.exc_info()
                if e.status_code == 400:
                    raise exception.SecurityGroupCannotBeRemoved(
                        six.text_type(e))
                else:
                    six.reraise(*exc_info)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Neutron Error:")

    def _refresh_neutron_extensions_cache(self):
        """Refresh the neutron extensions cache when necessary."""
        if (not self.last_neutron_extension_sync or
            ((time.time() - self.last_neutron_extension_sync)
             >= CONF.neutron.extension_sync_interval)):
            extensions_list = self.neutron_api.list_extensions()['extensions']
            self.last_neutron_extension_sync = time.time()
            self.extensions.clear()
            self.extensions = {ext['name']: ext for ext in extensions_list}

    def _has_port_binding_extension(self, refresh_cache=False):
        if refresh_cache:
            self._refresh_neutron_extensions_cache()
        return "Port Binding" in self.extensions

    def _populate_neutron_extension_values(self, container,
                                           pci_request_id,
                                           port_req_body):
        """Populate neutron extension values for the instance.

        If the extensions loaded contain QOS_QUEUE then pass the rxtx_factor.
        """
        self._refresh_neutron_extensions_cache()
        has_port_binding_extension = (
            self._has_port_binding_extension())
        if has_port_binding_extension:
            self._populate_neutron_binding_profile(container,
                                                   pci_request_id,
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
            port_req_body['port'][BINDING_PROFILE] = profile

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
