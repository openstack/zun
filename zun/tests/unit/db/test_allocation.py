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

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbAllocationTestCase(base.DbTestCase):

    def setUp(self):
        super(DbAllocationTestCase, self).setUp()

    def test_create_allocation(self):
        utils.create_test_allocation(context=self.context)

    def test_get_allocation_by_id(self):
        provider = utils.create_test_resource_provider(
            context=self.context)
        allocation = utils.create_test_allocation(
            resource_provider_id=provider.id, context=self.context)
        res = dbapi.get_allocation(self.context, allocation.id)
        self.assertEqual(allocation.id, res.id)

    def test_get_allocation_that_does_not_exist(self):
        allocation_id = 1111111
        self.assertRaises(exception.AllocationNotFound,
                          dbapi.get_allocation,
                          self.context,
                          allocation_id)

    def test_list_allocations(self):
        cids = []
        for i in range(1, 6):
            provider = utils.create_test_resource_provider(
                id=i,
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            allocation = utils.create_test_allocation(
                id=i,
                resource_provider_id=provider.id,
                consumer_id=uuidutils.generate_uuid(),
                context=self.context)
            cids.append(allocation['consumer_id'])
        res = dbapi.list_allocations(self.context)
        res_cids = [r.consumer_id for r in res]
        self.assertEqual(sorted(cids), sorted(res_cids))

    def test_list_allocations_sorted(self):
        cids = []
        for i in range(5):
            provider = utils.create_test_resource_provider(
                id=i,
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            allocation = utils.create_test_allocation(
                id=i,
                resource_provider_id=provider.id,
                consumer_id=uuidutils.generate_uuid(),
                context=self.context)
            cids.append(allocation['consumer_id'])
        res = dbapi.list_allocations(self.context,
                                     sort_key='consumer_id')
        res_cids = [r.consumer_id for r in res]
        self.assertEqual(sorted(cids), res_cids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_allocations,
                          self.context,
                          sort_key='foo')

    def test_list_allocations_with_filters(self):
        provider = utils.create_test_resource_provider(
            id=1,
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        allocation1 = utils.create_test_allocation(
            used=0,
            resource_provider_id=provider.id,
            context=self.context)
        allocation2 = utils.create_test_allocation(
            used=1,
            resource_provider_id=provider.id,
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
