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

import mock

from cinderclient import exceptions as cinder_exception
from oslo_utils import timeutils

import zun.conf
from zun.tests import base
from zun.volume import cinder_api


CONF = zun.conf.CONF


class FakeVolume(object):

    def __init__(self, volume_id, size=1, attachments=None, multiattach=False):
        self.id = volume_id
        self.name = 'volume_name'
        self.description = 'volume_description'
        self.status = 'available'
        self.created_at = timeutils.utcnow()
        self.size = size
        self.availability_zone = 'nova'
        self.attachments = attachments or []
        self.volume_type = 99
        self.bootable = False
        self.snapshot_id = 'snap_id_1'
        self.metadata = {}
        self.multiattach = multiattach


class TestingException(Exception):
    pass


class CinderApiTestCase(base.TestCase):

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_get(self, mock_cinderclient):
        volume_id = 'volume_id1'
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.get(volume_id)

        mock_cinderclient.assert_called_once_with()
        mock_volumes.get.assert_called_once_with(volume_id)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_reserve_volume(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.reserve_volume('id1')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.reserve.assert_called_once_with('id1')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_unreserve_volume(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.unreserve_volume('id1')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.unreserve.assert_called_once_with('id1')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_begin_detaching(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.begin_detaching('id1')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.begin_detaching.assert_called_once_with('id1')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_roll_detaching(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.roll_detaching('id1')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.roll_detaching.assert_called_once_with('id1')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_attach(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.attach('id1', 'point', 'host')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.attach.assert_called_once_with(
            volume='id1', mountpoint='point', host_name='host',
            instance_uuid=None)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_detach(self, mock_cinderclient):
        attachment = {'host_name': 'fake_host',
                      'attachment_id': 'fakeid'}

        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)
        mock_cinderclient.return_value.volumes.get.return_value = \
            FakeVolume('id1', attachments=[attachment])

        self.api = cinder_api.CinderAPI(self.context)
        self.api.detach('id1')

        mock_cinderclient.assert_called_with()
        mock_volumes.detach.assert_called_once_with('id1', None)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_detach_multiattach(self, mock_cinderclient):
        attachment = {'host_name': CONF.host,
                      'attachment_id': 'fakeid'}

        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)
        mock_cinderclient.return_value.volumes.get.return_value = \
            FakeVolume('id1', attachments=[attachment], multiattach=True)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.detach('id1')

        mock_cinderclient.assert_called_with()
        mock_volumes.detach.assert_called_once_with('id1', 'fakeid')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_initialize_connection(self, mock_cinderclient):
        connection_info = {'foo': 'bar'}
        mock_cinderclient.return_value.volumes. \
            initialize_connection.return_value = connection_info

        volume_id = 'fake_vid'
        connector = {'host': 'fakehost1'}
        self.api = cinder_api.CinderAPI(self.context)
        actual = self.api.initialize_connection(volume_id, connector)

        expected = connection_info
        self.assertEqual(expected, actual)

        mock_cinderclient.return_value.volumes. \
            initialize_connection.assert_called_once_with(volume_id, connector)

    @mock.patch('zun.volume.cinder_api.LOG')
    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_initialize_connection_exception_no_code(
            self, mock_cinderclient, mock_log):
        mock_cinderclient.return_value.volumes. \
            initialize_connection.side_effect = (
                cinder_exception.ClientException(500, "500"))
        mock_cinderclient.return_value.volumes. \
            terminate_connection.side_effect = (TestingException)

        connector = {'host': 'fakehost1'}
        self.api = cinder_api.CinderAPI(self.context)
        self.assertRaises(cinder_exception.ClientException,
                          self.api.initialize_connection,
                          'id1',
                          connector)
        self.assertIsNone(mock_log.error.call_args_list[1][0][1]['code'])

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_initialize_connection_rollback(self, mock_cinderclient):
        mock_cinderclient.return_value.volumes.\
            initialize_connection.side_effect = (
                cinder_exception.ClientException(500, "500"))

        connector = {'host': 'host1'}
        self.api = cinder_api.CinderAPI(self.context)
        ex = self.assertRaises(cinder_exception.ClientException,
                               self.api.initialize_connection,
                               'id1',
                               connector)
        self.assertEqual(500, ex.code)
        mock_cinderclient.return_value.volumes.\
            terminate_connection.assert_called_once_with('id1', connector)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_initialize_connection_no_rollback(self, mock_cinderclient):
        mock_cinderclient.return_value.volumes.\
            initialize_connection.side_effect = TestingException

        connector = {'host': 'host1'}
        self.api = cinder_api.CinderAPI(self.context)
        self.assertRaises(TestingException,
                          self.api.initialize_connection,
                          'id1',
                          connector)
        self.assertFalse(mock_cinderclient.return_value.volumes.
                         terminate_connection.called)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_terminate_connection(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        self.api = cinder_api.CinderAPI(self.context)
        self.api.terminate_connection('id1', 'connector')

        mock_cinderclient.assert_called_once_with()
        mock_volumes.terminate_connection.assert_called_once_with('id1',
                                                                  'connector')

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_create_volume(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        volume_size = '5'
        self.api = cinder_api.CinderAPI(self.context)
        self.api.create_volume(volume_size)

        mock_cinderclient.assert_called_once_with()
        mock_volumes.create.assert_called_once_with(volume_size)

    @mock.patch('zun.common.clients.OpenStackClients.cinder')
    def test_delete_volume(self, mock_cinderclient):
        mock_volumes = mock.MagicMock()
        mock_cinderclient.return_value = mock.MagicMock(volumes=mock_volumes)

        volume_id = self.id
        self.api = cinder_api.CinderAPI(self.context)
        self.api.delete_volume(volume_id)

        mock_cinderclient.assert_called_once_with()
        mock_volumes.delete.assert_called_once_with(volume_id)
