#    Copyright 2016 IBM Corp.
#
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

from zun.common import consts
from zun.common import exception
from zun.compute import api
from zun.compute import container_actions
import zun.conf
from zun import objects
from zun.tests import base
from zun.tests.unit.db import utils


CONF = zun.conf.CONF


class TestAPI(base.TestCase):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.compute_api = api.API(self.context)
        self.container = objects.Container(
            self.context, **utils.get_test_container())
        self.network = objects.Network(
            self.context, **utils.get_test_network())

    @mock.patch('zun.compute.api.API._record_action_start')
    @mock.patch('zun.compute.rpcapi.API.container_create')
    @mock.patch('zun.compute.rpcapi.API.image_search')
    @mock.patch('zun.compute.api.API._schedule_container')
    def test_container_create(self, mock_schedule_container,
                              mock_image_search,
                              mock_container_create,
                              mock_record_action_start):
        container = self.container
        container.status = consts.CREATING
        image_meta = mock.MagicMock()
        image_meta.id = '1234'
        mock_schedule_container.return_value = {'host': u'Centos',
                                                'nodename': None,
                                                'limits': {}}
        mock_image_search.return_value = [image_meta]
        self.compute_api.container_create(self.context, container,
                                          None, None, None, False)
        self.assertTrue(mock_schedule_container.called)
        self.assertTrue(mock_image_search.called)
        self.assertTrue(mock_container_create.called)

    @mock.patch('zun.compute.api.API._schedule_container')
    @mock.patch.object(objects.Container, 'save')
    def test_schedule_container_exception(self, mock_save,
                                          mock_schedule_container):
        container = self.container
        container.status = consts.CREATING
        mock_schedule_container.side_effect = exception.NoValidHost(
            reason='not enough host')
        self.compute_api.container_create(self.context, container,
                                          None, None, None, False)
        self.assertTrue(mock_schedule_container.called)
        self.assertTrue(mock_save.called)
        self.assertEqual(consts.ERROR, container.status)

    @mock.patch('zun.compute.rpcapi.API.image_search')
    @mock.patch('zun.compute.api.API._schedule_container')
    @mock.patch.object(objects.Container, 'save')
    def test_searching_image_exception(self, mock_save,
                                       mock_schedule_container,
                                       mock_image_search):
        container = self.container
        container.status = consts.CREATING
        mock_schedule_container.return_value = {'host': u'Centos',
                                                'nodename': None,
                                                'limits': {}}
        mock_image_search.side_effect = exception.ZunException

        self.assertRaises(exception.ZunException,
                          self.compute_api.container_create,
                          self.context, container,
                          None, None, None, False)
        self.assertTrue(mock_schedule_container.called)
        self.assertTrue(mock_image_search.called)
        self.assertTrue(mock_save.called)
        self.assertEqual(consts.ERROR, container.status)

    @mock.patch('zun.compute.rpcapi.API._call')
    def test_capsule_delete(self, mock_call):
        capsule = self.container
        self.compute_api.capsule_delete(
            self.context, capsule)
        mock_call.assert_called_once_with(
            capsule.host, "capsule_delete", capsule=capsule)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_delete(self, mock_start, mock_srv_list,
                              mock_srv_up, mock_cast):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_delete(
            self.context, container, False)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.DELETE, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_delete",
            container=container, force=False)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_show(self, mock_srv_list,
                            mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_show(
            self.context, container)
        mock_call.assert_called_once_with(
            container.host, "container_show",
            container=container)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_reboot(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_reboot(self.context, container, 10)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.REBOOT, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_reboot",
            container=container, timeout=10)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_stop(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_stop(
            self.context, container, 10)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.STOP, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_stop", container=container, timeout=10)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_start(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_start(
            self.context, container)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.START, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_start", container=container)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_pause(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_pause(
            self.context, container)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.PAUSE, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_pause", container=container)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_unpause(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_unpause(
            self.context, container)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.UNPAUSE, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_unpause", container=container)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_logs(self, mock_srv_list,
                            mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_logs(
            self.context, container, 1, 1, 1, 1, 1)
        mock_call.assert_called_once_with(
            container.host, "container_logs",
            container=container, stdout=1, stderr=1,
            timestamps=1, tail=1, since=1)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_exec(self, mock_srv_list,
                            mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_exec(
            self.context, container, "/bin/bash", True, True)
        mock_call.assert_called_once_with(
            container.host, "container_exec",
            container=container, command="/bin/bash",
            run=True, interactive=True)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_exec_interactive(
            self, mock_srv_list, mock_srv_up, mock_call):
        mock_call.return_value = {'token': 'fake-token',
                                  'exec_id': 'fake-exec-id'}
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        result = self.compute_api.container_exec(
            self.context, container, "/bin/bash", True, True)
        self.assertIn('fake-token', result['proxy_url'])
        self.assertIn('fake-exec-id', result['proxy_url'])
        mock_call.assert_called_once_with(
            container.host, "container_exec",
            container=container, command="/bin/bash",
            run=True, interactive=True)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_exec_resize(self, mock_srv_list,
                                   mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_exec_resize(
            self.context, container, '123', 10, 5)
        mock_call.assert_called_once_with(
            container.host, "container_exec_resize",
            exec_id='123', height=10, width=5)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_kill(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.container_kill(
            self.context, container, 9)
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.KILL, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "container_kill", container=container, signal=9)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_update(self, mock_srv_list,
                              mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_update(
            self.context, container, {})
        mock_call.assert_called_once_with(
            container.host, "container_update",
            container=container, patch={})

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_attach(self, mock_srv_list,
                              mock_srv_up, mock_call):
        mock_call.return_value = 'fake-token'
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        url = self.compute_api.container_attach(self.context, container)
        mock_call.assert_called_once_with(
            container.host, "container_attach",
            container=container)
        expected_url = '%s?token=%s&uuid=%s' % (
            CONF.websocket_proxy.base_url, 'fake-token', container.uuid)
        self.assertEqual(expected_url, url)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_resize(self, mock_srv_list,
                              mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_resize(self.context, container, 10, 5)
        mock_call.assert_called_once_with(
            container.host, "container_resize",
            container=container, height=10, width=5)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_top(self, mock_srv_list,
                           mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_top(self.context, container, "")
        mock_call.assert_called_once_with(
            container.host, "container_top",
            container=container, ps_args="")

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_get_archive(self, mock_srv_list,
                                   mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_get_archive(
            self.context, container, "/root")
        mock_call.assert_called_once_with(
            container.host, "container_get_archive",
            container=container, path="/root")

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_add_security_group(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.add_security_group(
            self.context, container, {})
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.ADD_SECURITY_GROUP, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "add_security_group",
            container=container, security_group={})

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_remove_security_group(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.remove_security_group(
            self.context, container, {})
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.REMOVE_SECURITY_GROUP, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "remove_security_group",
            container=container, security_group={})

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_put_archive(self, mock_srv_list,
                                   mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_put_archive(
            self.context, container, "/root", {})
        mock_call.assert_called_once_with(
            container.host, "container_put_archive",
            container=container, path="/root", data={})

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    def test_container_stats(self, mock_srv_list,
                             mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_stats(self.context, container)
        mock_call.assert_called_once_with(
            container.host, "container_stats",
            container=container)

    @mock.patch('zun.compute.rpcapi.API._call')
    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_container_commit(self, mock_start, mock_srv_list,
                              mock_srv_up, mock_call):
        container = self.container
        srv = objects.ZunService(
            self.context,
            **utils.get_test_zun_service(host=container.host))
        mock_srv_list.return_value = [srv]
        mock_srv_up.return_value = True
        self.compute_api.container_commit(
            self.context, container, "ubuntu", "latest")
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.COMMIT, want_result=False)
        mock_call.assert_called_once_with(
            container.host, "container_commit",
            container=container, repository="ubuntu", tag="latest")

    @mock.patch('zun.compute.rpcapi.API._call')
    def test_image_search(self, mock_call):
        self.compute_api.image_search(
            self.context, "ubuntu", "glance", True)
        mock_call.assert_called_once_with(
            None, "image_search", image="ubuntu",
            image_driver_name="glance", exact_match=True)

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_network_attach(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.network_attach(
            self.context, container, {})
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.NETWORK_ATTACH, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "network_attach", container=container,
            requested_network={})

    @mock.patch('zun.compute.rpcapi.API._cast')
    @mock.patch.object(objects.ContainerAction, 'action_start')
    def test_network_detach(self, mock_start, mock_cast):
        container = self.container
        self.compute_api.network_detach(
            self.context, container, {})
        mock_start.assert_called_once_with(
            self.context, container.uuid,
            container_actions.NETWORK_DETACH, want_result=False)
        mock_cast.assert_called_once_with(
            container.host, "network_detach", container=container, network={})

    @mock.patch('zun.compute.rpcapi.API.network_create')
    def test_network_create(self, mock_network_create):
        network = self.network
        self.compute_api.network_create(self.context, network)
        self.assertTrue(mock_network_create.called)
