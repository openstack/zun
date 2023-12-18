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

import math
import sys
import time

from neutronclient.common import exceptions
from oslo_log import log as logging
from oslo_utils import excutils

from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
import zun.conf
from zun.network import network
from zun.network import neutron
from zun import objects

CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)

DEVICE_OWNER = 'compute:kuryr'


class KuryrNetwork(network.Network):
    def init(self, context, docker_api):
        self.docker = docker_api
        self.neutron_api = neutron.NeutronAPI(context)
        self.context = context

    def get_or_create_network(self, context, neutron_net_id):
        docker_net_name = neutron_net_id
        docker_networks = self.docker.networks(names=[docker_net_name])
        if not docker_networks:
            self.create_network(neutron_net_id)

    def create_network(self, neutron_net_id):
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
        name = neutron_net_id
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
        network_dict['host'] = CONF.host
        network = objects.ZunNetwork(self.context, **network_dict)

        for attempt in (1, 2, 3):
            LOG.debug("Attempt (%s) to create network: %s", attempt, network)
            created_network = self._create_network_attempt(
                network, options, ipam_options)
            if created_network:
                return created_network
            backoff = int(math.pow(2, attempt) - 1)
            time.sleep(backoff)

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

            networks = objects.ZunNetwork.list(
                self.context,
                filters={'neutron_net_id': network.neutron_net_id,
                         'host': CONF.host})
            LOG.debug("network objects with 'neutron_net_id' as '%(net_id)s'"
                      "at host %(host)s: %(networks)s",
                      {"net_id": network.neutron_net_id,
                       "host": CONF.host,
                       "networks": networks})
            docker_networks = self.docker.networks(names=[network.name])
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

    def process_networking_config(self, container, requested_network,
                                  host_config, container_kwargs, docker,
                                  security_group_ids):
        docker_net_name = requested_network['network']
        neutron_net_id = requested_network['network']
        addresses, port = self.neutron_api.create_or_update_port(
            container, neutron_net_id, requested_network, DEVICE_OWNER,
            security_group_ids, set_binding_host=True)
        container.addresses = {requested_network['network']: addresses}

        ipv4_address = None
        ipv6_address = None
        for address in addresses:
            if address['version'] == 4:
                ipv4_address = address['addr']
            if address['version'] == 6:
                ipv6_address = address['addr']

        endpoint_config = docker.create_endpoint_config(
            ipv4_address=ipv4_address, ipv6_address=ipv6_address)
        network_config = docker.create_networking_config({
            docker_net_name: endpoint_config})

        host_config['network_mode'] = docker_net_name
        container_kwargs['networking_config'] = network_config
        container_kwargs['mac_address'] = port['mac_address']

    def connect_container_to_network(self, container, requested_network,
                                     security_groups=None):
        """Connect container to the network

        This method will create a neutron port, retrieve the ip address(es)
        of the port, and pass them to docker.connect_container_to_network.
        """
        network_name = requested_network['network']
        container_id = container.container_id

        neutron_net_id = requested_network['network']
        addresses, original_port = self.neutron_api.create_or_update_port(
            container, neutron_net_id, requested_network, DEVICE_OWNER,
            security_groups)

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
            port_req_body['port'][consts.BINDING_HOST_ID] = None
            port_req_body['port']['mac_address'] = port.get('mac_address')
            port_req_body['port'][consts.BINDING_PROFILE] = \
                port.get(consts.BINDING_PROFILE, {})

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

    def disconnect_container_from_network(self, container, neutron_network_id):
        network_name = neutron_network_id
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
            self.neutron_api.delete_or_unbind_ports(all_ports, neutron_ports)

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
                        str(e))
                else:
                    utils.reraise(*exc_info)
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
                        str(e))
                else:
                    utils.reraise(*exc_info)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Neutron Error:")

    def on_container_started(self, container):
        pass

    def on_container_stopped(self, container):
        pass
