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
import mock

import etcd
from etcd import Client as etcd_client
from oslo_config import cfg
from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils
import six

from zun.common import exception
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult


class DbImageTestCase(base.DbTestCase):

    def setUp(self):
        super(DbImageTestCase, self).setUp()

    def test_pull_image(self):
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")

    def test_pull_image_duplicate_repo(self):
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        utils.create_test_image(context=self.context,
                                repo="ubuntu:14.04")

    def test_pull_image_duplicate_tag(self):
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        utils.create_test_image(context=self.context,
                                repo="centos:latest")

    def test_pull_image_already_exists(self):
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_image,
                          context=self.context, repo="ubuntu:latest")

    def test_get_image_by_id(self):
        image = utils.create_test_image(context=self.context)
        res = self.dbapi.get_image_by_id(self.context, image.id)
        self.assertEqual(image.id, res.id)
        self.assertEqual(image.uuid, res.uuid)

    def test_get_image_by_uuid(self):
        image = utils.create_test_image(context=self.context)
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
                context=self.context, repo="testrepo" + str(i))
            uuids.append(six.text_type(image['uuid']))
        res = self.dbapi.list_images(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_images_sorted(self):
        uuids = []
        for i in range(5):
            image = utils.create_test_image(
                context=self.context, uuid=uuidutils.generate_uuid(),
                repo="testrepo" + str(i))
            uuids.append(six.text_type(image.uuid))
        res = self.dbapi.list_images(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.list_images,
                          self.context,
                          sort_key='foo')

    def test_list_images_with_filters(self):
        image1 = utils.create_test_image(
            context=self.context, repo='image-one',
            uuid=uuidutils.generate_uuid())
        image2 = utils.create_test_image(
            context=self.context, repo='image-two',
            uuid=uuidutils.generate_uuid())

        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'image-one'})
        self.assertEqual([image1.id], [r.id for r in res])

        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'image-two'})
        self.assertEqual([image2.id], [r.id for r in res])

        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'bad-image'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.list_images(
            self.context,
            filters={'repo': image1.repo})
        self.assertEqual([image1.id], [r.id for r in res])

    def test_update_image(self):
        image = utils.create_test_image(context=self.context)
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
        image = utils.create_test_image(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_image, image.id,
                          {'uuid': ''})


class EtcdDbImageTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbImageTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_pull_image(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_image(context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_pull_image_duplicate_repo(self, mock_get,
                                       mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        utils.create_test_image(context=self.context,
                                repo="ubuntu:14.04")

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_pull_image_duplicate_tag(self, mock_get,
                                      mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        utils.create_test_image(context=self.context,
                                repo="centos:14.04")

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_pull_image_already_exists(self, mock_get,
                                       mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_image(context=self.context,
                                repo="ubuntu:latest")
        mock_get.return_value = mock.MagicMock()
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_image,
                          context=self.context, repo="ubuntu:latest")

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_get_image_by_uuid(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        image = utils.create_test_image(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(image.as_dict())
        res = self.dbapi.get_image_by_uuid(self.context, image.uuid)
        self.assertEqual(image.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_image_that_does_not_exist(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ImageNotFound,
                          self.dbapi.get_image_by_uuid, self.context,
                          'db09ecea-7d63-4638-ae88-b8581f796e86')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_list_images(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuids = []
        images = []
        for i in range(1, 6):
            image = utils.create_test_image(context=self.context,
                                            repo='testrepo' + str(i))
            images.append(image.as_dict())
            uuids.append(image.uuid)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(images)
        res = self.dbapi.list_images(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_list_images_sorted(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuids = []
        images = []
        for i in range(1, 6):
            image = utils.create_test_image(context=self.context,
                                            repo='testrepo' + str(i))
            images.append(image.as_dict())
            uuids.append(image.uuid)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(images)
        res = self.dbapi.list_images(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]

        self.assertEqual(sorted(uuids), res_uuids)
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.list_images,
                          self.context, sort_key='foo')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_list_images_with_filters(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        image1 = utils.create_test_image(
            context=self.context, repo='imageone',
            uuid=uuidutils.generate_uuid())
        image2 = utils.create_test_image(
            context=self.context, repo='imagetwo',
            uuid=uuidutils.generate_uuid())
        images = [image1.as_dict(), image2.as_dict()]

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(images)
        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'imageone'})
        self.assertEqual([image1.uuid], [r.uuid for r in res])

        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'imagetwo'})
        self.assertEqual([image2.uuid], [r.uuid for r in res])

        res = self.dbapi.list_images(self.context,
                                     filters={'repo': 'foo'})
        self.assertEqual([], [r.uuid for r in res])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_update_image(self, mock_get, mock_update, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        image = utils.create_test_image(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(image.as_dict())
        self.dbapi.update_image(image.uuid, {'tag': 'newtag'})
        self.assertEqual('newtag', json.loads(
            mock_update.call_args_list[0][0][0].value)['tag'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_image_not_found(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ImageNotFound, self.dbapi.update_image,
                          'db09ecea-7d63-4638-ae88-b8581f796e86',
                          {'tag': 'newtag'})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch('zun.db.etcd.api.EtcdAPI.get_image_by_repo_and_tag')
    def test_update_image_uuid(self, mock_get, mock_write, mock_read):
        mock_get.return_value = None
        mock_read.side_effect = etcd.EtcdKeyNotFound
        image = utils.create_test_image(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_image, image.uuid,
                          {'uuid': 'newuuid'})
