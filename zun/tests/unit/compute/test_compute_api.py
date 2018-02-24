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
from zun.objects.container import Container
from zun.tests import base
from zun.tests.unit.db import utils


class TestAPI(base.TestCase):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.compute_api = api.API(self.context)

    @mock.patch('zun.compute.api.API._record_action_start')
    @mock.patch('zun.compute.rpcapi.API.container_create')
    @mock.patch('zun.compute.rpcapi.API.image_search')
    @mock.patch('zun.compute.api.API._schedule_container')
    def test_container_create(self, mock_schedule_container,
                              mock_image_search,
                              mock_container_create,
                              mock_record_action_start):
        container = Container(self.context, **utils.get_test_container())
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
    @mock.patch.object(Container, 'save')
    def test_schedule_container_exception(self, mock_save,
                                          mock_schedule_container):
        container = Container(self.context, **utils.get_test_container())
        container.status = consts.CREATING
        mock_schedule_container.side_effect = Exception
        self.compute_api.container_create(self.context, container,
                                          None, None, None, False)
        self.assertTrue(mock_schedule_container.called)
        self.assertTrue(mock_save.called)
        self.assertEqual(consts.ERROR, container.status)

    @mock.patch('zun.compute.rpcapi.API.image_search')
    @mock.patch('zun.compute.api.API._schedule_container')
    @mock.patch.object(Container, 'save')
    def test_searching_image_exception(self, mock_save,
                                       mock_schedule_container,
                                       mock_image_search):
        container = Container(self.context, **utils.get_test_container())
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
