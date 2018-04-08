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
import mock

from neutronclient.common import exceptions as n_exc

from zun.common import exception
from zun.network import kuryr_network
from zun.objects.container import Container
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

    def update_port(self, port_id, port):
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
        self.network_api = kuryr_network.KuryrNetwork()
        self.network_api.init(self.context, self.docker_api)
        self.network_api.neutron_api = FakeNeutronClient()

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_create_network_without_subnetpool(self,
                                               mock_neutron_api_cls):
        self.network_api.neutron_api.subnets[0].pop('subnetpool_id')
        mock_neutron_api_cls.return_value = self.network_api.neutron_api
        name = 'test_kuryr_network'
        neutron_net_id = 'fake-net-id'
        with mock.patch.object(self.network_api.docker, 'create_network',
                               return_value='docker-net'
                               ) as mock_create_network:
            docker_network = self.network_api.create_network(name,
                                                             neutron_net_id)
        self.assertEqual('docker-net', docker_network)
        mock_create_network.assert_called_once_with(
            name=name,
            driver='kuryr',
            enable_ipv6=False,
            ipam={'Config': [{'Subnet': '10.5.0.0/16', 'Gateway': '10.5.0.1'}],
                  'Driver': 'kuryr',
                  'Options': {'neutron.net.shared': 'False',
                              'neutron.subnet.uuid': 'fake-subnet-id',
                              'neutron.pool.uuid': None}},
            options={'neutron.net.uuid': 'fake-net-id',
                     'neutron.net.shared': 'False',
                     'neutron.subnet.uuid': 'fake-subnet-id',
                     'neutron.pool.uuid': None})

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_create_network_with_subnetpool(self,
                                            mock_neutron_api_cls):
        mock_neutron_api_cls.return_value = self.network_api.neutron_api
        name = 'test_kuryr_network'
        neutron_net_id = 'fake-net-id'
        with mock.patch.object(self.network_api.docker, 'create_network',
                               return_value='docker-net'
                               ) as mock_create_network:
            docker_network = self.network_api.create_network(name,
                                                             neutron_net_id)
        self.assertEqual('docker-net', docker_network)
        mock_create_network.assert_called_once_with(
            name=name,
            driver='kuryr',
            enable_ipv6=False,
            ipam={'Config': [{'Subnet': '10.5.0.0/16', 'Gateway': '10.5.0.1'}],
                  'Driver': 'kuryr',
                  'Options': {'neutron.net.shared': 'False',
                              'neutron.subnet.uuid': 'fake-subnet-id',
                              'neutron.pool.uuid': 'fake-subnetpool-id'}},
            options={'neutron.net.uuid': 'fake-net-id',
                     'neutron.net.shared': 'False',
                     'neutron.subnet.uuid': 'fake-subnet-id',
                     'neutron.pool.uuid': 'fake-subnetpool-id'})

    def test_remove_network(self):
        network_name = 'c02afe4e-8350-4263-8078'
        self.network_api.remove_network(network_name)

    def test_inspect_network(self):
        network_name = 'c02afe4e-8350-4263-8078'
        expected = {'Name': 'c02afe4e-8350-4263-8078',
                    'Options': {'neutron.net.uuid': '1234567'}}
        info = self.network_api.inspect_network(network_name)
        self.assertEqual(expected, info)

    def test_list_networks(self):
        expected = [{'Name': 'test_network'}]
        networks = self.network_api.list_networks()
        self.assertEqual(expected, networks)

    def test_connect_container_to_network(self):
        container = Container(self.context, **utils.get_test_container())
        network_name = 'c02afe4e-8350-4263-8078'
        requested_net = {'ipv4_address': '10.5.0.22',
                         'port': 'fake-port-id',
                         'preserve_on_delete': True}
        expected_address = [{'version': 4, 'addr': '10.5.0.22',
                             'port': 'fake-port-id',
                             'subnet_id': 'fake-subnet-id',
                             'preserve_on_delete': True}]
        old_port = self.network_api.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual('', old_port['device_id'])
        with mock.patch.object(self.network_api.docker,
                               'connect_container_to_network') as mock_connect:
            address = self.network_api.connect_container_to_network(
                container, network_name, requested_net)

        self.assertEqual(expected_address, address)
        mock_connect.assert_called_once_with(
            container.container_id, network_name, ipv4_address='10.5.0.22')
        new_port = self.network_api.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        self.assertEqual(container.uuid, new_port['device_id'])

    def test_disconnect_container_from_network(self):
        addresses = {'fake-net-id': [{'port': 'fake-port-id',
                                      'preserve_on_delete': False}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        network_name = 'c02afe4e-8350-4263-8078'
        ports = self.network_api.neutron_api.list_ports(
            id='fake-port-id')['ports']
        self.assertEqual(1, len(ports))
        with mock.patch.object(self.network_api.docker,
                               'disconnect_container_from_network'
                               ) as mock_disconnect:
            self.network_api.disconnect_container_from_network(
                container, network_name, 'fake-net-id')
        mock_disconnect.assert_called_once_with(
            container.container_id, network_name)
        # assert the neutron port is deleted
        ports = self.network_api.neutron_api.list_ports(
            id='fake-port-id')['ports']
        self.assertEqual(0, len(ports))

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_add_security_groups_to_ports(self, mock_neutron_api_cls):
        addresses = {'fake-net-id': [{'port': 'fake-port-id'}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        mock_neutron_api_cls.return_value = self.network_api.neutron_api
        old_port = self.network_api.neutron_api.list_ports(
            id='fake-port-id')['ports'][0]
        security_group_ids = ['sg2']
        self.network_api.add_security_groups_to_ports(container,
                                                      security_group_ids)
        new_port = self.network_api.neutron_api.list_ports(
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
        mock_neutron_api_cls.return_value = self.network_api.neutron_api
        security_group_ids = ['sg2']
        with mock.patch.object(self.network_api.neutron_api,
                               'update_port') as mock_update_port:
            mock_update_port.side_effect = n_exc.BadRequest(
                message='error')
            self.assertRaises(exception.SecurityGroupCannotBeApplied,
                              self.network_api.add_security_groups_to_ports,
                              container, security_group_ids)

        mock_update_port.assert_called_once_with(
            'fake-port-id',
            {'port': {'security_groups': ['sg1', 'sg2']}})
