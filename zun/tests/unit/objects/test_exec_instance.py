# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
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

from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestExecInstanceObject(base.DbTestCase):

    def setUp(self):
        super(TestExecInstanceObject, self).setUp()
        self.fake_exec_inst = utils.get_test_exec_instance()

    def test_list_by_container_id(self):
        with mock.patch.object(self.dbapi, 'list_exec_instances',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_exec_inst]
            exec_insts = objects.ExecInstance.list_by_container_id(
                self.context, 111)
            mock_get_list.assert_called_once_with(
                self.context, {'container_id': 111}, None, None, None, None)
            self.assertThat(exec_insts, HasLength(1))
            self.assertIsInstance(exec_insts[0], objects.ExecInstance)
            self.assertEqual(self.context, exec_insts[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_exec_instance',
                               autospec=True) as mock_create_exec_instance:
            mock_create_exec_instance.return_value = self.fake_exec_inst
            exec_inst = objects.ExecInstance(
                self.context, **self.fake_exec_inst)
            exec_inst.create(self.context)
            mock_create_exec_instance.assert_called_once_with(
                self.context, self.fake_exec_inst)
            self.assertEqual(self.context, exec_inst._context)
