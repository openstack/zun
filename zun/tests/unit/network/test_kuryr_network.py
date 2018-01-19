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
import mock

from neutronclient.common import exceptions as n_exc

from zun.common import exception
from zun.network import kuryr_network
from zun.objects.container import Container
from zun.tests import base
from zun.tests.unit.db import utils


class FakeNeutronClient(object):

    def list_subnets(self, **kwargs):
        return {'subnets': [{'ip_version': 4, 'subnetpool_id': '1234567',
                             'cidr': '255.255.255.0',
                             'gateway_ip': '192.168.2.0',
                             'id': '12345678'}]}

    def create_port(self, port_id):
        return {'port': {'fixed_ips': [{'ip_address': '192.168.2.22'}],
                         'id': '1234567'}}

    def update_port(self, port_id, port):
        pass

    def list_ports(self, **kwargs):
        return {'ports': [{'id': '1234567', 'security_groups': ['sg1']}]}

    def delete_port(self, port_id):
        pass

    def get_neutron_port(self, port_id):
        return {'fixed_ips': [{'ip_address': '192.168.2.22'}],
                'id': '1234567',
                'security_groups': []}

    def get_neutron_network(self, network_id):
        return {'shared': False}

    def list_subnetpools(self, **kwargs):
        return {'subnetpools': [{
            'address_scope_id': None,
            'default_prefixlen': 8,
            'id': '9b13e2fc-d565-4a3d-9a4c-9a14050e5010',
            'ip_version': 4,
            'prefixes': ['10.5.0.0/16'],
            'tags': ['06be906d-fe20-41af-b0e4-d770e185e7c8'],
            'name': 'test_subnet_pool-'
        }]}


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

    @mock.patch.object(kuryr_network.KuryrNetwork, '_get_subnetpool')
    def test_create_network_with_subnet_has_subnetpool(self,
                                                       mock_get_subnetpool):
        name = 'test_kuryr_network'
        neutron_net_id = '1234567'
        expected = {'Warning': '',
                    'Id': '7372099cdcecbc9918d3666440b73a170d9690'}
        docker_network = self.network_api.create_network(name, neutron_net_id)
        mock_get_subnetpool.return_value = \
            '06be906d-fe20-41af-b0e4-d770e185e7c8'
        self.assertEqual(expected, docker_network)

    @mock.patch.object(kuryr_network.KuryrNetwork, '_get_subnetpool')
    def test_create_network_without_subnetpool(self,
                                               mock_get_subnetpool):
        name = 'test_kuryr_network'
        neutron_net_id = '1234567'
        expected = {'Warning': '',
                    'Id': '7372099cdcecbc9918d3666440b73a170d9690'}
        docker_network = self.network_api.create_network(name, neutron_net_id)
        mock_get_subnetpool.return_value = None
        self.assertEqual(expected, docker_network)

    @mock.patch.object(kuryr_network.KuryrNetwork, '_get_subnetpool')
    def test_create_network_with_subnetpool(self,
                                            mock_get_subnetpool):
        name = 'test_kuryr_network'
        neutron_net_id = '1234567'
        expected = {'Warning': '',
                    'Id': '7372099cdcecbc9918d3666440b73a170d9690'}
        docker_network = self.network_api.create_network(name, neutron_net_id)
        mock_get_subnetpool.return_value = \
            self.network_api.neutron_api.list_subnetpools().get('subnetpools')
        self.assertEqual(expected, docker_network)

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
        kwargs = {'ip_version': 4, 'ipv4_address': '192.168.2.22',
                  'port': '1234567', 'preserve_on_delete': True}
        expected = [{'version': 4, 'addr': '192.168.2.22',
                     'port': '1234567', 'preserve_on_delete': True}]
        address = self.network_api.connect_container_to_network(container,
                                                                network_name,
                                                                kwargs)
        self.assertEqual(expected, address)

    def test_disconnect_container_from_network(self):
        container = Container(self.context, **utils.get_test_container())
        network_name = 'c02afe4e-8350-4263-8078'
        self.network_api.disconnect_container_from_network(container,
                                                           network_name)

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_add_security_groups_to_ports(self, mock_neutron_api_cls):
        addresses = {'private': [{'port': '1234567'}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        mock_neutron_api = mock.MagicMock()
        mock_neutron_api_cls.return_value = mock_neutron_api
        self.network_api.neutron_api.context = mock.Mock()
        security_group_ids = ['sg2']
        self.network_api.add_security_groups_to_ports(container,
                                                      security_group_ids)
        mock_neutron_api.update_port.assert_called_once_with(
            '1234567',
            {'port': {'security_groups': ['sg1', 'sg2']}})

    @mock.patch('zun.network.neutron.NeutronAPI')
    def test_add_security_groups_to_ports_bad_update(
            self, mock_neutron_api_cls):
        addresses = {'private': [{'port': '1234567'}]}
        container = Container(self.context, **utils.get_test_container(
            addresses=addresses))
        mock_neutron_api = mock.MagicMock()
        mock_neutron_api_cls.return_value = mock_neutron_api
        self.network_api.neutron_api.context = mock.Mock()
        security_group_ids = ['sg2']
        mock_neutron_api.update_port.side_effect = n_exc.BadRequest(
            message='error')
        self.assertRaises(exception.SecurityGroupCannotBeApplied,
                          self.network_api.add_security_groups_to_ports,
                          container, security_group_ids)
        mock_neutron_api.update_port.assert_called_once_with(
            '1234567',
            {'port': {'security_groups': ['sg1', 'sg2']}})
