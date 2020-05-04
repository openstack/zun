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


class DbRegistryTestCase(base.DbTestCase):

    def setUp(self):
        super(DbRegistryTestCase, self).setUp()

    def test_create_registry(self):
        username = 'fake-user'
        password = 'fake-pass'
        registry = utils.create_test_registry(context=self.context,
                                              username=username,
                                              password=password)
        self.assertEqual(username, registry.username)
        self.assertEqual(password, registry.password)

    def test_create_registry_already_exists(self):
        utils.create_test_registry(context=self.context,
                                   uuid='123')
        with self.assertRaisesRegex(exception.RegistryAlreadyExists,
                                    'A registry with UUID 123.*'):
            utils.create_test_registry(context=self.context,
                                       uuid='123')

    def test_get_registry_by_uuid(self):
        username = 'fake-user'
        password = 'fake-pass'
        registry = utils.create_test_registry(context=self.context,
                                              username=username,
                                              password=password)
        res = dbapi.get_registry_by_uuid(self.context,
                                         registry.uuid)
        self.assertEqual(registry.id, res.id)
        self.assertEqual(registry.uuid, res.uuid)
        self.assertEqual(username, res.username)
        self.assertEqual(password, res.password)

    def test_get_registry_by_name(self):
        username = 'fake-user'
        password = 'fake-pass'
        registry = utils.create_test_registry(context=self.context,
                                              username=username,
                                              password=password)
        res = dbapi.get_registry_by_name(
            self.context, registry.name)
        self.assertEqual(registry.id, res.id)
        self.assertEqual(registry.uuid, res.uuid)
        self.assertEqual(username, res.username)
        self.assertEqual(password, res.password)

    def test_get_registry_that_does_not_exist(self):
        self.assertRaises(exception.RegistryNotFound,
                          dbapi.get_registry_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_registries(self):
        uuids = []
        passwords = []
        for i in range(1, 6):
            password = 'pass' + str(i)
            passwords.append(password)
            registry = utils.create_test_registry(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='registry' + str(i),
                password=password)
            uuids.append(str(registry['uuid']))
        res = dbapi.list_registries(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))
        res_passwords = [r.password for r in res]
        self.assertEqual(sorted(passwords), sorted(res_passwords))

    def test_list_registries_sorted(self):
        uuids = []
        for i in range(5):
            registry = utils.create_test_registry(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='registry' + str(i))
            uuids.append(str(registry.uuid))
        res = dbapi.list_registries(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_registries,
                          self.context,
                          sort_key='foo')

    def test_list_registries_with_filters(self):
        registry1 = utils.create_test_registry(
            name='registry-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        registry2 = utils.create_test_registry(
            name='registry-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_registries(
            self.context, filters={'name': 'registry-one'})
        self.assertEqual([registry1.id], [r.id for r in res])

        res = dbapi.list_registries(
            self.context, filters={'name': 'registry-two'})
        self.assertEqual([registry2.id], [r.id for r in res])

        res = dbapi.list_registries(
            self.context, filters={'name': 'bad-registry'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_registries(
            self.context,
            filters={'name': registry1.name})
        self.assertEqual([registry1.id], [r.id for r in res])

    def test_list_registries_with_list_filters(self):
        registry1 = utils.create_test_registry(
            name='registry-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        registry2 = utils.create_test_registry(
            name='registry-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_registries(
            self.context, filters={'name': ['registry-one', 'registry-two']})
        uuids = sorted([registry1.uuid, registry2.uuid])
        self.assertEqual(uuids, sorted([r.uuid for r in res]))

    def test_destroy_registry(self):
        registry = utils.create_test_registry(context=self.context)
        dbapi.destroy_registry(self.context, registry.id)
        self.assertRaises(exception.RegistryNotFound,
                          dbapi.get_registry_by_uuid,
                          self.context, registry.uuid)

    def test_destroy_registry_by_uuid(self):
        registry = utils.create_test_registry(context=self.context)
        dbapi.destroy_registry(self.context, registry.uuid)
        self.assertRaises(exception.RegistryNotFound,
                          dbapi.get_registry_by_uuid,
                          self.context, registry.uuid)

    def test_destroy_registry_that_does_not_exist(self):
        self.assertRaises(exception.RegistryNotFound,
                          dbapi.destroy_registry, self.context,
                          uuidutils.generate_uuid())

    def test_update_registry(self):
        registry = utils.create_test_registry(context=self.context)
        old_name = registry.name
        new_name = 'new-name'
        new_password = 'new-pass'
        self.assertNotEqual(old_name, new_name)

        res = dbapi.update_registry(self.context, registry.id,
                                    {'name': new_name,
                                     'password': new_password})
        self.assertEqual(new_name, res.name)
        self.assertEqual(new_password, res.password)

    def test_update_registry_not_found(self):
        registry_uuid = uuidutils.generate_uuid()
        new_name = 'new-name'
        self.assertRaises(exception.RegistryNotFound,
                          dbapi.update_registry, self.context,
                          registry_uuid, {'name': new_name})

    def test_update_registry_uuid(self):
        registry = utils.create_test_registry(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_registry, self.context,
                          registry.id, {'uuid': ''})
