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

from zun.common import exception
from zun.compute import rpcapi
from zun import objects
from zun.tests import base
from zun.tests.unit.db import utils


class TestAPI(base.TestCase):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.compute_rpcapi = rpcapi.API()

    @mock.patch('zun.api.servicegroup.ServiceGroup.service_is_up')
    @mock.patch('zun.objects.ZunService.list_by_binary')
    @mock.patch('zun.common.rpc_service.API._call')
    def test_container_delete_with_host_no_tup(self, mock_rpc_call,
                                               mock_list, mock_service_is_up):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        test_service = utils.get_test_zun_service(host="fake_host")
        test_service_obj = objects.ZunService(self.context, **test_service)
        mock_list.return_value = [test_service_obj]
        mock_service_is_up.return_value = False
        self.assertRaises(exception.ContainerHostNotUp,
                          self.compute_rpcapi.container_delete,
                          self.context, test_container_obj, False)
