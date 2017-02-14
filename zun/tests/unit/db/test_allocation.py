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

from oslo_config import cfg

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbAllocationTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('db_type', 'sql')
        super(DbAllocationTestCase, self).setUp()

    def test_create_allocation(self):
        utils.create_test_allocation(context=self.context)

    def test_get_allocation_by_id(self):
        allocation = utils.create_test_allocation(context=self.context)
        res = dbapi.get_allocation(self.context, allocation.id)
        self.assertEqual(allocation.id, res.id)

    def test_get_allocation_that_does_not_exist(self):
        allocation_id = 1111111
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.get_allocation,
                          self.context,
                          allocation_id)

    def test_list_allocations(self):
        rcs = []
        for i in range(1, 6):
            allocation = utils.create_test_allocation(
                id=i,
                resource_class_id=i,
                context=self.context)
            rcs.append(allocation['resource_class_id'])
        res = dbapi.list_allocations(self.context)
        res_rcs = [r.resource_class_id for r in res]
        self.assertEqual(sorted(rcs), sorted(res_rcs))

    def test_list_allocations_sorted(self):
        rcs = []
        for i in range(5):
            allocation = utils.create_test_allocation(
                id=i,
                resource_class_id=i,
                context=self.context)
            rcs.append(allocation.resource_class_id)
        res = dbapi.list_allocations(self.context,
                                     sort_key='resource_class_id')
        res_rcs = [r.resource_class_id for r in res]
        self.assertEqual(sorted(rcs), res_rcs)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_allocations,
                          self.context,
                          sort_key='foo')

    def test_list_allocations_with_filters(self):
        allocation1 = utils.create_test_allocation(
            used=0,
            resource_class_id=1,
            context=self.context)
        allocation2 = utils.create_test_allocation(
            used=1,
            resource_class_id=2,
            context=self.context)

        res = dbapi.list_allocations(
            self.context, filters={'used': 0})
        self.assertEqual([allocation1.id], [r.id for r in res])

        res = dbapi.list_allocations(
            self.context, filters={'used': 1})
        self.assertEqual([allocation2.id], [r.id for r in res])

        res = dbapi.list_allocations(
            self.context, filters={'used': 11111})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_allocations(
            self.context,
            filters={'used': allocation1.used})
        self.assertEqual([allocation1.id], [r.id for r in res])

    def test_destroy_allocation(self):
        allocation = utils.create_test_allocation(context=self.context)
        dbapi.destroy_allocation(self.context, allocation.id)
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.get_allocation,
                          self.context, allocation.id)

    def test_destroy_allocation_by_id(self):
        allocation = utils.create_test_allocation(context=self.context)
        dbapi.destroy_allocation(self.context, allocation.id)
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.get_allocation,
                          self.context, allocation.id)

    def test_destroy_allocation_that_does_not_exist(self):
        allocation_id = 1111111
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.destroy_allocation, self.context,
                          allocation_id)

    def test_update_allocation(self):
        allocation = utils.create_test_allocation(context=self.context)
        old_used = allocation.used
        new_used = 0
        self.assertNotEqual(old_used, new_used)

        res = dbapi.update_allocation(self.context, allocation.id,
                                      {'used': new_used})
        self.assertEqual(new_used, res.used)

    def test_update_allocation_not_found(self):
        allocation_id = 11111111
        new_used = 0
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.update_allocation, self.context,
                          allocation_id, {'used': new_used})
