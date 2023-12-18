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
"""
Tests For kuryr network
"""
import copy
from unittest import mock

from neutronclient.common import exceptions as n_exc

from zun.common import exception
from zun import conf
from zun.network import kuryr_network
from zun.objects.container import Container
from zun.objects.zun_network import ZunNetwork
from zun.tests import base
from zun.tests.unit.db import utils


class FakeNeutronClient(object):

    def __init__(self):
        super(FakeNeutronClient, self).__init__()
        self.networks = [{'id': 'fake-net-id',
                          'name': 'fake-net-name',
                          'tenant_id': 'fake_project',
                          'shared': False}]
        self.subnets = [{'ip_version': 4,
                         'subnetpool_id': 'fake-subnetpool-id',
                         'cidr': '10.5.0.0/16',
                         'gateway_ip': '10.5.0.1',
                         'tenant_id': 'fake_project',
                         'network_id': 'fake-net-id',
                         'id': 'fake-subnet-id'}]
        self.ports = [{'id': 'fake-port-id',
                       'fixed_ips': [{
                           'ip_address': '10.5.0.22',
                           'subnet_id': 'fake-subnet-id'}],
                       'device_id': '',
                       'tenant_id': 'fake_project',
                       'security_groups': ['sg1']}]
        self.subnetpools = [{'address_scope_id': None,
                             'default_prefixlen': 8,
                             'id': 'fake-subnetpool-id',
                             'ip_version': 4,
                             'prefixes': ['10.5.0.0/16'],
                             'tags': ['06be906d-fe20-41af-b0e4-d770e185e7c8'],
                             'tenant_id': 'fake_project',
                             'name': 'test_subnet_pool-'}]

    def list_subnets(self, **filters):
        subnets = list(self.subnets)
        for subnet in self.subnets:
            for attr in filters:
                if subnet[attr] != filters[attr]:
                    subnets.remove(subnet)
        return {'subnets': copy.deepcopy(subnets)}

    def create_port(self, port):
        port_data = copy.deepcopy(port['port'])
        self.ports.append(port_data)
        return port

    def update_port(self, port_id, port, **kwargs):
        port_data = copy.deepcopy(port['port'])
        for port in self.ports:
            if port['id'] == port_id:
                port.update(port_data)

    def list_ports(self, **filters):
        ports = list(self.ports)
        for port in self.ports:
            for attr in filters:
                if port[attr] != filters[attr]:
                    ports.remove(port)
        return {'ports': copy.deepcopy(ports)}

    def create_or_update_port(self, container, network_uuid,
                              requested_network, device_owner,
                              security_groups=None, **kwargs):
        if requested_network.get('port'):
            neutron_port_id = requested_network.get('port')
            neutron_port = self.get_neutron_port(neutron_port_id)
            # update device_id in port
            port_req_body = {'port': {'device_id': container.uuid}}
            self.update_port(neutron_port_id, port_req_body)
        else:
            port_dict = {
                'network_id': network_uuid,
                'tenant_id': self.context.project_id,
                'device_id': container.uuid,
            }
            ip_addr = requested_network.get("fixed_ip")
            if ip_addr:
                port_dict['fixed_ips'] = [{'ip_address': ip_addr}]
            neutron_port = self.create_port({'port': port_dict})
            neutron_port = neutron_port['port']

        addresses = []
        for fixed_ip in neutron_port['fixed_ips']:
            addresses.append({
                'addr': fixed_ip['ip_address'],
                'version': 4,
                'port': neutron_port['id'],
                'subnet_id': fixed_ip['subnet_id'],
                'preserve_on_delete': requested_network['preserve_on_delete'],
            })

        return addresses, neutron_port

    def delete_or_unbind_ports(self, ports, ports_to_delete):
        for port_id in ports:
            if port_id in ports_to_delete:
                self.delete_port(port_id)
            else:
                port_req_body = {'port': {'device_id': ''}}
                self.update_port(port_id, port_req_body)

    def delete_port(self, port_id):
        for port in self.ports:
            if port['id'] == port_id:
                self.ports.remove(port)
                return

    def get_neutron_port(self, port_id):
        for port in self.ports:
            if port['id'] == port_id:
                return copy.deepcopy(port)

    def get_neutron_network(self, network_id):
        for network in self.networks:
            if network['id'] == network_id or network['name'] == network_id:
                return copy.deepcopy(network)

    def list_subnetpools(self, **filters):
        subnetpools = list(self.subnetpools)
        for subnetpool in self.subnetpools:
            for attr in filters:
                if subnetpool[attr] != filters[attr]:
                    subnetpools.remove(subnetpool)
        return {'subnetpools': copy.deepcopy(subnetpools)}


class FakeDockerClient(object):

    def create_network(self, **kwargs):
        return {'Warning': '',
                'Id': '7372099cdcecbc9918d3666440b73a170d9690'}

    def remove_network(self, network_name):
        pass

    def inspect_network(self, network_name):
        return {'Name': 'c02afe4e-8350-4263-8078',
                'Options': {'neutron.net.uuid': '1234567'}}

    def networks(self, **kwargs):
        return [{'Name': 'test_network'}]

    def connect_container_to_network(self, container_id, network_name,
                                     **kwargs):
        pass

    def disconnect_container_from_network(self, container_id,
                                          network_name):
        pass


class KuryrNetworkTestCase(base.TestCase):
    """Test casse for kuryr network"""

    def setUp(self):
        super(KuryrNetworkTestCase, self).setUp()
        self.docker_api = FakeDockerClient()
        self.network_driver = kuryr_network.KuryrNetwork()
        self.network_driver.init(self.context, self.docker_api)
        self.network_driver.neutron_api = FakeNeutronClient()

    @mock.patch.object(ZunNetwork, 'create')
    @mock.patch.object(ZunNetwork, 'save')
    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_create_network_without_subnetpool(
            self, mock_neutron_api_cls, mock_save, mock_create):
        self.network_driver.neutron_api.subnets[0].pop('subnetpool_id')
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        neutron_net_id = 'fake-net-id'
        with mock.patch.object(self.network_driver.docker, 'create_network',
                               return_value={'Id': 'docker-net'}
                               ) as mock_create_network:
            network = self.network_driver.create_network(neutron_net_id)
        self.assertEqual('docker-net', network.network_id)
        mock_create_network.assert_called_once_with(
            name=neutron_net_id,
            driver='kuryr',
            enable_ipv6=False,
            ipam={'Config': [{'Subnet': '10.5.0.0/16', 'Gateway': '10.5.0.1'}],
                  'Driver': 'kuryr',
                  'Options': {'neutron.net.shared': 'False',
                              'neutron.subnet.uuid': 'fake-subnet-id'}},
            options={'neutron.net.uuid': 'fake-net-id',
                     'neutron.net.shared': 'False',
                     'neutron.subnet.uuid': 'fake-subnet-id'})

    @mock.patch.object(ZunNetwork, 'create')
    @mock.patch.object(ZunNetwork, 'save')
    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_create_network_with_subnetpool(
            self, mock_neutron_api_cls, mock_save, mock_create):
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        neutron_net_id = 'fake-net-id'
        with mock.patch.object(self.network_driver.docker, 'create_network',
                               return_value={'Id': 'docker-net'}
                               ) as mock_create_network:
            network = self.network_driver.create_network(neutron_net_id)
        self.assertEqual('docker-net', network.network_id)
        mock_create_network.assert_called_once_with(
            name=neutron_net_id,
            driver='kuryr',
            enable_ipv6=False,
            ipam={'Config': [{'Subnet': '10.5.0.0/16', 'Gateway': '10.5.0.1'}],
                  'Driver': 'kuryr',
                  'Options': {'neutron.net.shared': 'False',
                              'neutron.subnet.uuid': 'fake-subnet-id'}},
            options={'neutron.net.uuid': 'fake-net-id',
                     'neutron.net.shared': 'False',
                     'neutron.subnet.uuid': 'fake-subnet-id'})

    @mock.patch.object(ZunNetwork, 'create')
    @mock.patch.object(ZunNetwork, 'save')
    @mock.patch.object(ZunNetwork, 'list')
    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_create_network_already_exist(
            self, mock_neutron_api_cls, mock_list, mock_save, mock_create):
        fake_host = 'host1'
        conf.CONF.set_override('host', fake_host)
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        neutron_net_id = 'fake-net-id'
        docker_net_id = 'docker-net'
        fake_network = mock.Mock()
        fake_network.network_id = docker_net_id
        mock_list.return_value = [fake_network]
        mock_create.side_effect = exception.NetworkAlreadyExists(
            field='neutron_net_id', value=neutron_net_id)
        with mock.patch.object(self.network_driver.docker, 'networks',
                               return_value=[{'Id': docker_net_id}]
                               ) as mock_list_network:
            network = self.network_driver.create_network(neutron_net_id)
        self.assertEqual(docker_net_id, network.network_id)
        mock_list.assert_called_once_with(
            self.context, filters={'neutron_net_id': neutron_net_id,
                                   'host': fake_host})
        mock_list_network.assert_called_once_with(names=[neutron_net_id])

    def test_remove_network(self):
        network = mock.Mock(name='c02afe4e-8350-4263-8078')
        self.network_driver.remove_network(network)
        network.destroy.assert_called_once_with()

    def test_connect_container_to_network(self):
        container = Container(self.context, **utils.get_test_container())
        network_name = 'c02afe4e-8350-4263-8078'
        requested_net = {'ipv4_address': '10.5.0.22',
                         'port': 'fake-port-id',
                         'network': network_name,
                         'preserve_on_delete': True}
        expected_address = [{'version': 4, 'addr': '10.5.0.22',
                             'port': 'fake-port-id',
                             'subnet_id': 'fake-subnet-id',
                             'preserve_on_delete': True}]
        old_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual('', old_port['device_id'])
        with mock.patch.object(self.network_driver.docker,
                               'connect_container_to_network') as mock_connect:
            address = self.network_driver.connect_container_to_network(
                container, requested_net)

        self.assertEqual(expected_address, address)
        mock_connect.assert_called_once_with(
            container.container_id, network_name, ipv4_address='10.5.0.22')
        new_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual(container.uuid, new_port['device_id'])

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_connect_container_to_network_failed(self, mock_neutron_api_cls):
        container = Container(self.context, **utils.get_test_container())
        network_name = 'c02afe4e-8350-4263-8078'
        requested_net = {'ipv4_address': '10.5.0.22',
                         'network': network_name,
                         'port': 'fake-port-id',
                         'preserve_on_delete': True}
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        old_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual('', old_port['device_id'])
        self.network_driver.docker = mock.MagicMock()
        self.network_driver.docker.connect_container_to_network = \
            mock.Mock(side_effect=exception.DockerError)
        self.assertRaises(exception.DockerError,
                          self.network_driver.connect_container_to_network,
                          container, requested_net)
        new_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual('', new_port['device_id'])

    def test_disconnect_container_from_network(self):
        addresses = {'fake-net-id': [{'port': 'fake-port-id',
                                      'preserve_on_delete': False}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        ports = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports']
        self.assertEqual(1, len(ports))
        with mock.patch.object(self.network_driver.docker,
                               'disconnect_container_from_network'
                               ) as mock_disconnect:
            self.network_driver.disconnect_container_from_network(
                container, 'fake-net-id')
        mock_disconnect.assert_called_once_with(
            container.container_id, 'fake-net-id')
        # assert the neutron port is deleted
        ports = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports']
        self.assertEqual(0, len(ports))

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_add_security_groups_to_ports(self, mock_neutron_api_cls):
        addresses = {'fake-net-id': [{'port': 'fake-port-id'}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        old_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        security_group_ids = ['sg2']
        self.network_driver.add_security_groups_to_ports(container,
                                                         security_group_ids)
        new_port = self.network_driver.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        old_secgroups = old_port.pop('security_groups')
        new_secgroups = new_port.pop('security_groups')
        self.assertEqual(old_secgroups + ['sg2'], new_secgroups)
        # assert nothing else changed besides security_groups
        self.assertEqual(old_port, new_port)

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_add_security_groups_to_ports_bad_update(
            self, mock_neutron_api_cls):
        addresses = {'fake-net-id': [{'port': 'fake-port-id'}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        mock_neutron_api_cls.return_value = self.network_driver.neutron_api
        security_group_ids = ['sg2']
        with mock.patch.object(self.network_driver.neutron_api,
                               'update_port') as mock_update_port:
            mock_update_port.side_effect = n_exc.BadRequest(
                message='error')
            self.assertRaises(exception.SecurityGroupCannotBeApplied,
                              self.network_driver.add_security_groups_to_ports,
                              container, security_group_ids)

        mock_update_port.assert_called_once_with(
            'fake-port-id',
            {'port': {'security_groups': ['sg1', 'sg2']}},
            admin=True)
