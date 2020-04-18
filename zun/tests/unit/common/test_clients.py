# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from cinderclient import client as cinderclient
from glanceclient import client as glanceclient
from neutronclient.v2_0 import client as neutronclient

from zun.common import clients
import zun.conf
from zun.tests import base


class ClientsTest(base.BaseTestCase):

    def setUp(self):
        super(ClientsTest, self).setUp()

        zun.conf.CONF.set_override('www_authenticate_uri',
                                   'http://server.test:5000/v2.0',
                                   group='keystone_authtoken')
        zun.conf.CONF.import_opt('api_version', 'zun.conf.glance_client',
                                 group='glance_client')

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_url_for(self, mock_keystone):
        obj = clients.OpenStackClients(None)
        obj.url_for(service_type='fake_service', interface='fake_endpoint')

        mock_endpoint = mock_keystone.return_value.session.get_endpoint
        mock_endpoint.assert_called_once_with(service_type='fake_service',
                                              interface='fake_endpoint')

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_zun_url(self, mock_keystone):
        fake_region = 'fake_region'
        fake_endpoint = 'fake_endpoint'
        zun.conf.CONF.set_override('region_name', fake_region,
                                   group='zun_client')
        zun.conf.CONF.set_override('endpoint_type', fake_endpoint,
                                   group='zun_client')
        obj = clients.OpenStackClients(None)
        obj.zun_url()

        mock_endpoint = mock_keystone.return_value.session.get_endpoint
        mock_endpoint.assert_called_once_with(region_name=fake_region,
                                              service_type='container',
                                              interface=fake_endpoint)

    @mock.patch.object(glanceclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def _test_clients_glance(self, expected_region_name, mock_keystone,
                             mock_call):
        mock_session = mock_keystone.return_value.session
        mock_session.get_endpoint.return_value = 'glance_url'
        fake_region = 'fake_region'
        fake_endpoint = 'fake_endpoint'
        zun.conf.CONF.set_override('region_name', fake_region,
                                   group='glance_client')
        zun.conf.CONF.set_override('endpoint_type', fake_endpoint,
                                   group='glance_client')
        con = mock.MagicMock()
        obj = clients.OpenStackClients(con)
        obj._glance = None
        obj.glance()

        mock_session.get_endpoint.assert_called_once_with(
            region_name=fake_region, service_type='image',
            interface=fake_endpoint)
        mock_call.assert_called_once_with(
            zun.conf.CONF.glance_client.api_version,
            endpoint='glance_url',
            session=mock_session)

    def test_clients_glance(self):
        self._test_clients_glance(None)

    def test_clients_glance_region(self):
        zun.conf.CONF.set_override('region_name',
                                   'myregion', group='glance_client')
        self._test_clients_glance('myregion')

    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_clients_glance_cached(self, mock_keystone):
        mock_keystone.return_value.session.get_endpoint.return_value = \
            'glance_url'
        con = mock.MagicMock()
        obj = clients.OpenStackClients(con)
        obj._glance = None
        glance = obj.glance()
        glance_cached = obj.glance()
        self.assertEqual(glance, glance_cached)

    @mock.patch.object(neutronclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_clients_neturon(self, mock_keystone, mock_call):
        ca_file = '/testpath'
        insecure = True
        zun.conf.CONF.set_override('ca_file', ca_file,
                                   group='neutron_client')
        zun.conf.CONF.set_override('insecure', insecure,
                                   group='neutron_client')
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        obj = clients.OpenStackClients(con)
        obj._neutron = None
        obj.neutron()
        mock_call.assert_called_once()

    @mock.patch.object(cinderclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'keystone')
    def test_clients_cinder(self, mock_keystone, mock_call):
        ca_file = '/testpath'
        insecure = True
        endpoint_type = 'internalURL'
        zun.conf.CONF.set_override('ca_file', ca_file,
                                   group='cinder_client')
        zun.conf.CONF.set_override('insecure', insecure,
                                   group='cinder_client')
        zun.conf.CONF.set_override('endpoint_type', endpoint_type,
                                   group='cinder_client')
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        obj = clients.OpenStackClients(con)
        obj._cinder = None
        obj.cinder()
        mock_call.assert_called_once()
