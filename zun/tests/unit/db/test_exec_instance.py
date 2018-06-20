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

from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbExecInstanceTestCase(base.DbTestCase):

    def setUp(self):
        super(DbExecInstanceTestCase, self).setUp()

    def test_create_exec_instance(self):
        utils.create_test_exec_instance(context=self.context)

    def test_create_exec_instance_already_exists(self):
        utils.create_test_exec_instance(context=self.context,
                                        container_id=1, exec_id='test-id')
        with self.assertRaisesRegex(
                exception.ExecInstanceAlreadyExists,
                'An exec instance with exec_id test-id .*'):
            utils.create_test_exec_instance(
                context=self.context, container_id=1, exec_id='test-id')

    def test_list_exec_instances(self):
        exec_ids = []
        for i in range(1, 6):
            exec_inst = utils.create_test_exec_instance(
                id=i,
                context=self.context,
                container_id=1,
                exec_id=uuidutils.generate_uuid())
            exec_ids.append(six.text_type(exec_inst['exec_id']))
        res = dbapi.list_exec_instances(self.context)
        res_exec_ids = [r.exec_id for r in res]
        self.assertEqual(sorted(exec_ids), sorted(res_exec_ids))

    def test_list_exec_instances_sorted(self):
        exec_ids = []
        for i in range(5):
            exec_inst = utils.create_test_exec_instance(
                id=i,
                context=self.context,
                container_id=1,
                exec_id=uuidutils.generate_uuid())
            exec_ids.append(six.text_type(exec_inst['exec_id']))
        res = dbapi.list_exec_instances(self.context, sort_key='exec_id')
        res_exec_ids = [r.exec_id for r in res]
        self.assertEqual(sorted(exec_ids), res_exec_ids)

    def test_list_exec_instances_with_filters(self):
        exec_inst1 = utils.create_test_exec_instance(
            id=1,
            context=self.context,
            container_id=1,
            exec_id='exec-one')
        exec_inst2 = utils.create_test_exec_instance(
            id=2,
            context=self.context,
            container_id=2,
            exec_id='exec-two')

        res = dbapi.list_exec_instances(
            self.context, filters={'container_id': 1})
        self.assertEqual([exec_inst1.id], [r.id for r in res])

        res = dbapi.list_exec_instances(
            self.context, filters={'container_id': 2})
        self.assertEqual([exec_inst2.id], [r.id for r in res])

        res = dbapi.list_exec_instances(
            self.context, filters={'container_id': 777})
        self.assertEqual([], [r.id for r in res])
