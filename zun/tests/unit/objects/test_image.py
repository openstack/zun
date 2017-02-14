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


class TestImageObject(base.DbTestCase):

    def setUp(self):
        super(TestImageObject, self).setUp()
        self.fake_image = utils.get_test_image()

    def test_get_by_uuid(self):
        uuid = self.fake_image['uuid']
        with mock.patch.object(self.dbapi, 'get_image_by_uuid',
                               autospec=True) as mock_get_image:
            mock_get_image.return_value = self.fake_image
            image = objects.Image.get_by_uuid(self.context, uuid)
            mock_get_image.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, image._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_images',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_image]
            images = objects.Image.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(images, HasLength(1))
            self.assertIsInstance(images[0], objects.Image)
            self.assertEqual(self.context, images[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_images',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_image]
            filt = {'id': '1'}
            images = objects.Image.list(self.context, filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(images, HasLength(1))
            self.assertIsInstance(images[0], objects.Image)
            self.assertEqual(self.context, images[0]._context)
            mock_get_list.assert_called_once_with(self.context,
                                                  filters=filt,
                                                  limit=None, marker=None,
                                                  sort_key=None, sort_dir=None)

    def test_pull(self):
        with mock.patch.object(self.dbapi, 'pull_image',
                               autospec=True) as mock_pull_image:
            mock_pull_image.return_value = self.fake_image
            image = objects.Image(self.context, **self.fake_image)
            image.pull(self.context)
            mock_pull_image.assert_called_once_with(self.context,
                                                    self.fake_image)
            self.assertEqual(self.context, image._context)

    def test_save(self):
        uuid = self.fake_image['uuid']
        with mock.patch.object(self.dbapi, 'get_image_by_uuid',
                               autospec=True) as mock_get_image:
            mock_get_image.return_value = self.fake_image
            with mock.patch.object(self.dbapi, 'update_image',
                                   autospec=True) as mock_update_image:
                image = objects.Image.get_by_uuid(self.context, uuid)
                image.repo = 'image-test'
                image.tag = '512'
                image.save()

                mock_get_image.assert_called_once_with(self.context, uuid)
                mock_update_image.assert_called_once_with(uuid,
                                                          {'repo':
                                                           'image-test',
                                                           'tag': '512'})
                self.assertEqual(self.context, image._context)
