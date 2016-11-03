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

import mock

from glanceclient import client as glanceclient

from zun.common import clients
from zun.common import exception
import zun.conf
from zun.tests import base


class ClientsTest(base.BaseTestCase):

    def setUp(self):
        super(ClientsTest, self).setUp()

        zun.conf.CONF.set_override('auth_uri', 'http://server.test:5000/v2.0',
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
    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def _test_clients_glance(self, expected_region_name, mock_auth, mock_url,
                             mock_call):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        obj.glance()
        mock_call.assert_called_once_with(
            zun.conf.CONF.glance_client.api_version,
            endpoint='url_from_keystone', username=None,
            token='3bcc3d3a03f44e3d8377f9247b0ad155',
            auth_url='keystone_url',
            password=None, cacert=None, cert=None, key=None, insecure=False)
        mock_url.assert_called_once_with(service_type='image',
                                         interface='publicURL',
                                         region_name=expected_region_name)

    def test_clients_glance(self):
        self._test_clients_glance(None)

    def test_clients_glance_region(self):
        zun.conf.CONF.set_override('region_name',
                                   'myregion', group='glance_client')
        self._test_clients_glance('myregion')

    def test_clients_glance_noauth(self):
        con = mock.MagicMock()
        con.auth_token = None
        con.auth_token_info = None
        auth_url = mock.PropertyMock(name="auth_url",
                                     return_value="keystone_url")
        type(con).auth_url = auth_url
        con.get_url_for = mock.Mock(name="get_url_for")
        con.get_url_for.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        self.assertRaises(exception.AuthorizationFailure, obj.glance)

    @mock.patch.object(clients.OpenStackClients, 'url_for')
    @mock.patch.object(clients.OpenStackClients, 'auth_url')
    def test_clients_glance_cached(self, mock_auth, mock_url):
        mock_auth.__get__ = mock.Mock(return_value="keystone_url")
        con = mock.MagicMock()
        con.auth_token = "3bcc3d3a03f44e3d8377f9247b0ad155"
        con.auth_url = "keystone_url"
        mock_url.return_value = "url_from_keystone"
        obj = clients.OpenStackClients(con)
        obj._glance = None
        glance = obj.glance()
        glance_cached = obj.glance()
        self.assertEqual(glance, glance_cached)
