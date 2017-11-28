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
from os_brick import exception as os_brick_exception
from oslo_serialization import jsonutils

import zun.conf
from zun.tests import base
from zun.volume import cinder_workflow


CONF = zun.conf.CONF


class CinderWorkflowTestCase(base.TestCase):

    def setUp(self):
        super(CinderWorkflowTestCase, self).setUp()
        self.fake_volume_id = 'fake-volume-id-1'
        self.fake_conn_prprts = {
            'ip': '10.3.4.5',
            'host': 'fakehost1'
        }
        self.fake_device_info = {
            'path': '/foo'
        }
        self.fake_conn_info = {
            'driver_volume_type': 'fake',
            'data': {},
        }

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_attach_volume(self,
                           mock_cinder_api_cls,
                           mock_get_connector_prprts,
                           mock_get_volume_connector):
        mock_cinder_api, mock_connector = self._test_attach_volume(
            mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector)

        mock_cinder_api.reserve_volume.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.initialize_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_connector.connect_volume.assert_called_once_with(
            self.fake_conn_info['data'])
        mock_cinder_api.attach.assert_called_once_with(
            volume_id=self.fake_volume_id,
            mountpoint=self.fake_device_info['path'],
            hostname=CONF.host)
        mock_connector.disconnect_volume.assert_not_called()
        mock_cinder_api.terminate_connection.assert_not_called()
        mock_cinder_api.detach.assert_not_called()
        mock_cinder_api.unreserve_volume.assert_not_called()

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_attach_volume_fail_reserve_volume(
            self, mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector):
        mock_cinder_api, mock_connector = self._test_attach_volume(
            mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector, fail_reserve=True)

        mock_cinder_api.reserve_volume.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.initialize_connection.assert_not_called()
        mock_connector.connect_volume.assert_not_called()
        mock_cinder_api.attach.assert_not_called()
        mock_connector.disconnect_volume.assert_not_called()
        mock_cinder_api.terminate_connection.assert_not_called()
        mock_cinder_api.detach.assert_not_called()
        mock_cinder_api.unreserve_volume.assert_called_once_with(
            self.fake_volume_id)

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_attach_volume_fail_initialize_connection(
            self, mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector):
        mock_cinder_api, mock_connector = self._test_attach_volume(
            mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector, fail_init=True)

        mock_cinder_api.reserve_volume.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.initialize_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_connector.connect_volume.assert_not_called()
        mock_cinder_api.attach.assert_not_called()
        mock_connector.disconnect_volume.assert_not_called()
        mock_cinder_api.terminate_connection.assert_not_called()
        mock_cinder_api.detach.assert_not_called()
        mock_cinder_api.unreserve_volume.assert_called_once_with(
            self.fake_volume_id)

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_attach_volume_fail_connect_volume(
            self, mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector):
        mock_cinder_api, mock_connector = self._test_attach_volume(
            mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector, fail_connect=True)

        mock_cinder_api.reserve_volume.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.initialize_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_connector.connect_volume.assert_called_once_with(
            self.fake_conn_info['data'])
        mock_cinder_api.attach.assert_not_called()
        mock_connector.disconnect_volume.assert_not_called()
        mock_cinder_api.terminate_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_cinder_api.detach.assert_not_called()
        mock_cinder_api.unreserve_volume.assert_called_once_with(
            self.fake_volume_id)

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_attach_volume_fail_attach(self,
                                       mock_cinder_api_cls,
                                       mock_get_connector_prprts,
                                       mock_get_volume_connector):
        mock_cinder_api, mock_connector = self._test_attach_volume(
            mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector, fail_attach=True)

        mock_cinder_api.reserve_volume.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.initialize_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_connector.connect_volume.assert_called_once_with(
            self.fake_conn_info['data'])
        mock_cinder_api.attach.assert_called_once_with(
            volume_id=self.fake_volume_id,
            mountpoint=self.fake_device_info['path'],
            hostname=CONF.host)
        mock_connector.disconnect_volume.assert_called_once_with(
            self.fake_conn_info['data'], None)
        mock_cinder_api.terminate_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_cinder_api.detach.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.unreserve_volume.assert_called_once_with(
            self.fake_volume_id)

    def _test_attach_volume(self,
                            mock_cinder_api_cls,
                            mock_get_connector_prprts,
                            mock_get_volume_connector,
                            fail_reserve=False, fail_init=False,
                            fail_connect=False, fail_attach=False):
        volume = mock.MagicMock()
        volume.volume_id = self.fake_volume_id
        mock_cinder_api = mock.MagicMock()
        mock_cinder_api_cls.return_value = mock_cinder_api
        mock_connector = mock.MagicMock()
        mock_get_connector_prprts.return_value = self.fake_conn_prprts
        mock_get_volume_connector.return_value = mock_connector
        mock_cinder_api.initialize_connection.return_value = \
            self.fake_conn_info
        mock_connector.connect_volume.return_value = self.fake_device_info
        cinder = cinder_workflow.CinderWorkflow(self.context)

        if fail_reserve:
            mock_cinder_api.reserve_volume.side_effect = \
                cinder_exception.ClientException(400)
            self.assertRaises(cinder_exception.ClientException,
                              cinder.attach_volume, volume)
        elif fail_init:
            mock_cinder_api.initialize_connection.side_effect = \
                cinder_exception.ClientException(400)
            self.assertRaises(cinder_exception.ClientException,
                              cinder.attach_volume, volume)
        elif fail_connect:
            mock_connector.connect_volume.side_effect = \
                os_brick_exception.BrickException()
            self.assertRaises(os_brick_exception.BrickException,
                              cinder.attach_volume, volume)
        elif fail_attach:
            mock_cinder_api.attach.side_effect = \
                cinder_exception.ClientException(400)
            self.assertRaises(cinder_exception.ClientException,
                              cinder.attach_volume, volume)
        else:
            device_path = cinder.attach_volume(volume)
            self.assertEqual('/foo', device_path)

        return mock_cinder_api, mock_connector

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_detach_volume(self,
                           mock_cinder_api_cls,
                           mock_get_connector_prprts,
                           mock_get_volume_connector):
        volume = mock.MagicMock()
        volume.volume_id = self.fake_volume_id
        volume.connection_info = jsonutils.dumps(self.fake_conn_info)
        mock_cinder_api = mock.MagicMock()
        mock_cinder_api_cls.return_value = mock_cinder_api
        mock_connector = mock.MagicMock()
        mock_get_connector_prprts.return_value = self.fake_conn_prprts
        mock_get_volume_connector.return_value = mock_connector

        cinder = cinder_workflow.CinderWorkflow(self.context)
        cinder.detach_volume(volume)

        mock_cinder_api.begin_detaching.assert_called_once_with(
            self.fake_volume_id)
        mock_connector.disconnect_volume.assert_called_once_with(
            self.fake_conn_info['data'], None)
        mock_cinder_api.terminate_connection.assert_called_once_with(
            self.fake_volume_id, self.fake_conn_prprts)
        mock_cinder_api.detach.assert_called_once_with(
            self.fake_volume_id)
        mock_cinder_api.roll_detaching.assert_not_called()

    @mock.patch('zun.volume.cinder_workflow.get_volume_connector')
    @mock.patch('zun.volume.cinder_workflow.get_volume_connector_properties')
    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_detach_volume_fail_disconnect(
            self, mock_cinder_api_cls, mock_get_connector_prprts,
            mock_get_volume_connector):
        volume = mock.MagicMock()
        volume.volume_id = self.fake_volume_id
        volume.connection_info = jsonutils.dumps(self.fake_conn_info)
        mock_cinder_api = mock.MagicMock()
        mock_cinder_api_cls.return_value = mock_cinder_api
        mock_connector = mock.MagicMock()
        mock_get_connector_prprts.return_value = self.fake_conn_prprts
        mock_get_volume_connector.return_value = mock_connector
        mock_connector.disconnect_volume.side_effect = \
            os_brick_exception.BrickException()

        cinder = cinder_workflow.CinderWorkflow(self.context)
        self.assertRaises(os_brick_exception.BrickException,
                          cinder.detach_volume, volume)

        mock_cinder_api.begin_detaching.assert_called_once_with(
            self.fake_volume_id)
        mock_connector.disconnect_volume.assert_called_once_with(
            self.fake_conn_info['data'], None)
        mock_cinder_api.terminate_connection.assert_not_called()
        mock_cinder_api.detach.assert_not_called()
        mock_cinder_api.roll_detaching.assert_called_once_with(
            self.fake_volume_id)

    @mock.patch('zun.volume.cinder_api.CinderAPI')
    def test_delete_volume(self,
                           mock_cinder_api_cls):
        volume = mock.MagicMock()
        volume.volume_id = self.fake_volume_id
        volume.connection_info = jsonutils.dumps(self.fake_conn_info)
        mock_cinder_api = mock.MagicMock()
        mock_cinder_api_cls.return_value = mock_cinder_api

        cinder = cinder_workflow.CinderWorkflow(self.context)
        cinder.delete_volume(volume)

        mock_cinder_api.delete_volume.assert_called_once_with(
            self.fake_volume_id)
