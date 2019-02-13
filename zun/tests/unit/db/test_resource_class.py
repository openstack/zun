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

"""Tests for manipulating resource classes via the DB API"""
from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbResourceClassTestCase(base.DbTestCase):

    def setUp(self):
        super(DbResourceClassTestCase, self).setUp()

    def test_create_resource_class(self):
        utils.create_test_resource_class(context=self.context)

    def test_create_resource_class_already_exists(self):
        utils.create_test_resource_class(
            context=self.context, uuid='123')
        with self.assertRaisesRegex(exception.ResourceClassAlreadyExists,
                                    'A resource class with uuid 123.*'):
            utils.create_test_resource_class(
                context=self.context, uuid='123')

    def test_get_resource_class_by_uuid(self):
        resource = utils.create_test_resource_class(context=self.context)
        res = dbapi.get_resource_class(self.context, resource.uuid)
        self.assertEqual(resource.uuid, res.uuid)
        self.assertEqual(resource.name, res.name)

    def test_get_resource_class_by_name(self):
        resource = utils.create_test_resource_class(context=self.context)
        res = dbapi.get_resource_class(self.context, resource.name)
        self.assertEqual(resource.id, res.id)
        self.assertEqual(resource.name, res.name)

    def test_get_resource_class_that_does_not_exist(self):
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.get_resource_class,
                          self.context, uuidutils.generate_uuid())

    def test_list_resource_classes(self):
        names = []
        for i in range(1, 6):
            resource = utils.create_test_resource_class(
                context=self.context,
                uuid=uuidutils.generate_uuid(),
                name='class' + str(i))
            names.append(six.text_type(resource['name']))
        res = dbapi.list_resource_classes(self.context)
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), sorted(res_names))

    def test_list_resource_classes_sorted(self):
        names = []
        for i in range(5):
            resource = utils.create_test_resource_class(
                context=self.context,
                uuid=uuidutils.generate_uuid(),
                name='class' + str(i))
            names.append(six.text_type(resource.name))
        res = dbapi.list_resource_classes(self.context, sort_key='name')
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), res_names)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_resource_classes,
                          self.context,
                          sort_key='foo')

    def test_destroy_resource_class(self):
        resource = utils.create_test_resource_class(context=self.context)
        dbapi.destroy_resource_class(self.context, resource.id)
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.get_resource_class,
                          self.context, resource.id)

    def test_destroy_resource_class_that_does_not_exist(self):
        bad_id = 1111111
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.destroy_resource_class, self.context,
                          bad_id)

    def test_update_resource_class(self):
        resource = utils.create_test_resource_class(context=self.context)
        old_name = resource.name
        new_name = 'new-name'
        self.assertNotEqual(old_name, new_name)

        res = dbapi.update_resource_class(
            self.context, resource.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_resource_class_not_found(self):
        bad_id = 1111111
        new_name = 'new-name'
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.update_resource_class, self.context,
                          bad_id, {'name': new_name})
