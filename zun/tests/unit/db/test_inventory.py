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


class DbInventoryTestCase(base.DbTestCase):

    def setUp(self):
        super(DbInventoryTestCase, self).setUp()

    def test_create_inventory(self):
        utils.create_test_inventory(context=self.context)

    def test_create_inventory_already_exists(self):
        utils.create_test_inventory(
            context=self.context, resource_provider_id=1, resource_class_id=1)
        fields = {'resource_provider_id': 1, 'resource_class_id': 1}
        with self.assertRaisesRegex(exception.UniqueConstraintViolated,
                                    'A resource with %s *' % fields):
            utils.create_test_inventory(
                context=self.context, resource_provider_id=1,
                resource_class_id=1)

    def test_get_inventory_by_id(self):
        provider = utils.create_test_resource_provider(
            context=self.context)
        inventory = utils.create_test_inventory(
            resource_provider_id=provider.id, context=self.context)
        res = dbapi.get_inventory(self.context, inventory.id)
        self.assertEqual(inventory.id, res.id)

    def test_get_inventory_that_does_not_exist(self):
        inventory_id = 1111111
        self.assertRaises(exception.InventoryNotFound,
                          dbapi.get_inventory,
                          self.context,
                          inventory_id)

    def test_list_inventories(self):
        totals = []
        for i in range(1, 6):
            provider = utils.create_test_resource_provider(
                id=i,
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            inventory = utils.create_test_inventory(
                id=i,
                resource_provider_id=provider.id,
                total=i,
                context=self.context)
            totals.append(inventory['total'])
        res = dbapi.list_inventories(self.context)
        res_totals = [r.total for r in res]
        self.assertEqual(sorted(totals), sorted(res_totals))

    def test_list_inventories_sorted(self):
        totals = []
        for i in range(5):
            provider = utils.create_test_resource_provider(
                id=i,
                uuid=uuidutils.generate_uuid(),
                context=self.context)
            inventory = utils.create_test_inventory(
                id=i,
                resource_provider_id=provider.id,
                total=10 - i,
                context=self.context)
            totals.append(inventory['total'])
        res = dbapi.list_inventories(self.context,
                                     sort_key='total')
        res_totals = [r.total for r in res]
        self.assertEqual(sorted(totals), res_totals)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_inventories,
                          self.context,
                          sort_key='foo')

    def test_list_inventories_with_filters(self):
        provider = utils.create_test_resource_provider(
            context=self.context)
        inventory1 = utils.create_test_inventory(
            total=10,
            resource_provider_id=provider.id,
            resource_class_id=1,
            context=self.context)
        inventory2 = utils.create_test_inventory(
            total=20,
            resource_provider_id=provider.id,
            resource_class_id=2,
            context=self.context)

        res = dbapi.list_inventories(
            self.context, filters={'total': 10})
        self.assertEqual([inventory1.id], [r.id for r in res])

        res = dbapi.list_inventories(
            self.context, filters={'total': 20})
        self.assertEqual([inventory2.id], [r.id for r in res])

        res = dbapi.list_inventories(
            self.context, filters={'total': 11111})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_inventories(
            self.context,
            filters={'total': inventory1.total})
        self.assertEqual([inventory1.id], [r.id for r in res])

    def test_destroy_inventory(self):
        inventory = utils.create_test_inventory(context=self.context)
        dbapi.destroy_inventory(self.context, inventory.id)
        self.assertRaises(exception.InventoryNotFound,
                          dbapi.get_inventory,
                          self.context, inventory.id)

    def test_destroy_inventory_by_id(self):
        inventory = utils.create_test_inventory(context=self.context)
        dbapi.destroy_inventory(self.context, inventory.id)
        self.assertRaises(exception.InventoryNotFound,
                          dbapi.get_inventory,
                          self.context, inventory.id)

    def test_destroy_inventory_that_does_not_exist(self):
        inventory_id = 1111111
        self.assertRaises(exception.InventoryNotFound,
                          dbapi.destroy_inventory, self.context,
                          inventory_id)

    def test_update_inventory(self):
        inventory = utils.create_test_inventory(context=self.context)
        old_total = inventory.total
        new_total = 100
        self.assertNotEqual(old_total, new_total)

        res = dbapi.update_inventory(self.context, inventory.id,
                                     {'total': new_total})
        self.assertEqual(new_total, res.total)

    def test_update_inventory_not_found(self):
        inventory_id = 11111111
        new_total = 'new-total'
        self.assertRaises(exception.InventoryNotFound,
                          dbapi.update_inventory, self.context,
                          inventory_id, {'total': new_total})
