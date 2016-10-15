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

"""Tests for manipulating Images via the DB API"""
from oslo_utils import uuidutils
import six

from zun.common import exception
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class DbImageTestCase(base.DbTestCase):

    def test_create_image(self):
        utils.create_test_image(repo="ubuntu:latest")

    def test_create_image_duplicate_repo(self):
        utils.create_test_image(repo="ubuntu:latest")
        utils.create_test_image(repo="ubuntu:14.04")

    def test_create_image_duplicate_tag(self):
        utils.create_test_image(repo="ubuntu:latest")
        utils.create_test_image(repo="centos:latest")

    def test_create_image_already_exists(self):
        utils.create_test_image(repo="ubuntu:latest")
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_image,
                          repo="ubuntu:latest")

    def test_get_image_by_id(self):
        image = utils.create_test_image()
        res = self.dbapi.get_image_by_id(self.context, image.id)
        self.assertEqual(image.id, res.id)
        self.assertEqual(image.uuid, res.uuid)

    def test_get_image_by_uuid(self):
        image = utils.create_test_image()
        res = self.dbapi.get_image_by_uuid(self.context, image.uuid)
        self.assertEqual(image.id, res.id)
        self.assertEqual(image.uuid, res.uuid)

    def test_get_image_that_does_not_exist(self):
        self.assertRaises(exception.ImageNotFound,
                          self.dbapi.get_image_by_id, self.context, 99)
        self.assertRaises(exception.ImageNotFound,
                          self.dbapi.get_image_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_images(self):
        uuids = []
        for i in range(1, 6):
            image = utils.create_test_image(
                repo="testrepo" + str(i))
            uuids.append(six.text_type(image['uuid']))
        res = self.dbapi.list_image(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_image_sorted(self):
        uuids = []
        for _ in range(5):
            image = utils.create_test_image(
                uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(image.uuid))
        res = self.dbapi.list_image(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.list_image,
                          self.context,
                          sort_key='foo')

    def test_list_image_with_filters(self):
        image1 = utils.create_test_image(
            repo='image-one',
            uuid=uuidutils.generate_uuid())
        image2 = utils.create_test_image(
            repo='image-two',
            uuid=uuidutils.generate_uuid())

        res = self.dbapi.list_image(self.context,
                                    filters={'repo': 'image-one'})
        self.assertEqual([image1.id], [r.id for r in res])

        res = self.dbapi.list_image(self.context,
                                    filters={'repo': 'image-two'})
        self.assertEqual([image2.id], [r.id for r in res])

        res = self.dbapi.list_image(self.context,
                                    filters={'repo': 'bad-image'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.list_image(
            self.context,
            filters={'repo': image1.repo})
        self.assertEqual([image1.id], [r.id for r in res])

    def test_update_image(self):
        image = utils.create_test_image()
        old_size = image.size
        new_size = '2000'
        self.assertNotEqual(old_size, new_size)

        res = self.dbapi.update_image(image.id,
                                      {'size': new_size})
        self.assertEqual(new_size, res.size)

    def test_update_image_not_found(self):
        image_uuid = uuidutils.generate_uuid()
        new_size = '2000'
        self.assertRaises(exception.ImageNotFound,
                          self.dbapi.update_image,
                          image_uuid, {'size': new_size})

    def test_update_image_uuid(self):
        image = utils.create_test_image()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_image, image.id,
                          {'uuid': ''})
