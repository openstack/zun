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

"""Tests for manipulating resource providers via the DB API"""

from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbResourceProviderTestCase(base.DbTestCase):

    def setUp(self):
        super(DbResourceProviderTestCase, self).setUp()

    def test_create_resource_provider(self):
        utils.create_test_resource_provider(context=self.context)

    def test_create_resource_provider_already_exists(self):
        utils.create_test_resource_provider(
            context=self.context, uuid='123')
        with self.assertRaisesRegex(exception.ResourceProviderAlreadyExists,
                                    'A resource provider with UUID 123.*'):
            utils.create_test_resource_provider(
                context=self.context, uuid='123')

    def test_get_resource_provider_by_uuid(self):
        provider = utils.create_test_resource_provider(context=self.context)
        res = dbapi.get_resource_provider(
            self.context, provider.uuid)
        self.assertEqual(provider.id, res.id)
        self.assertEqual(provider.uuid, res.uuid)

    def test_get_resource_provider_by_name(self):
        provider = utils.create_test_resource_provider(context=self.context)
        res = dbapi.get_resource_provider(
            self.context, provider.name)
        self.assertEqual(provider.id, res.id)
        self.assertEqual(provider.uuid, res.uuid)

    def test_get_resource_provider_that_does_not_exist(self):
        self.assertRaises(exception.ResourceProviderNotFound,
                          dbapi.get_resource_provider,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_resource_providers(self):
        uuids = []
        for i in range(1, 6):
            provider = utils.create_test_resource_provider(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='provider' + str(i))
            uuids.append(six.text_type(provider['uuid']))
        res = dbapi.list_resource_providers(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_resource_providers_sorted(self):
        uuids = []
        for i in range(5):
            provider = utils.create_test_resource_provider(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='provider' + str(i))
            uuids.append(six.text_type(provider.uuid))
        res = dbapi.list_resource_providers(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_resource_providers,
                          self.context,
                          sort_key='foo')

    def test_list_resource_providers_with_filters(self):
        provider1 = utils.create_test_resource_provider(
            name='provider-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        provider2 = utils.create_test_resource_provider(
            name='provider-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_resource_providers(
            self.context, filters={'name': 'provider-one'})
        self.assertEqual([provider1.id], [r.id for r in res])

        res = dbapi.list_resource_providers(
            self.context, filters={'name': 'provider-two'})
        self.assertEqual([provider2.id], [r.id for r in res])

        res = dbapi.list_resource_providers(
            self.context, filters={'name': 'bad-provider'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_resource_providers(
            self.context,
            filters={'name': provider1.name})
        self.assertEqual([provider1.id], [r.id for r in res])

    def test_destroy_resource_provider(self):
        provider = utils.create_test_resource_provider(context=self.context)
        dbapi.destroy_resource_provider(self.context, provider.id)
        self.assertRaises(exception.ResourceProviderNotFound,
                          dbapi.get_resource_provider,
                          self.context, provider.uuid)

    def test_destroy_resource_provider_by_uuid(self):
        provider = utils.create_test_resource_provider(context=self.context)
        dbapi.destroy_resource_provider(self.context, provider.uuid)
        self.assertRaises(exception.ResourceProviderNotFound,
                          dbapi.get_resource_provider,
                          self.context, provider.uuid)

    def test_destroy_resource_provider_that_does_not_exist(self):
        self.assertRaises(exception.ResourceProviderNotFound,
                          dbapi.destroy_resource_provider, self.context,
                          uuidutils.generate_uuid())

    def test_update_resource_provider(self):
        provider = utils.create_test_resource_provider(context=self.context)
        old_name = provider.name
        new_name = 'new-name'
        self.assertNotEqual(old_name, new_name)

        res = dbapi.update_resource_provider(
            self.context, provider.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_resource_provider_not_found(self):
        provider_uuid = uuidutils.generate_uuid()
        new_name = 'new-name'
        self.assertRaises(exception.ResourceProviderNotFound,
                          dbapi.update_resource_provider, self.context,
                          provider_uuid, {'name': new_name})

    def test_update_resource_provider_uuid(self):
        provider = utils.create_test_resource_provider(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_resource_provider, self.context,
                          provider.id, {'uuid': ''})
