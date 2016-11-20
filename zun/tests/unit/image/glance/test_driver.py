# Copyright 2016 Intel.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import os
import shutil
import tempfile

from zun.common import exception
import zun.conf
from zun.image.glance import driver
from zun.tests import base

CONF = zun.conf.CONF


class TestDriver(base.BaseTestCase):
    def setUp(self):
        super(TestDriver, self).setUp()
        self.driver = driver.GlanceDriver()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the directory after the test
        super(TestDriver, self).tearDown()
        shutil.rmtree(self.test_dir)

    @mock.patch.object(driver.GlanceDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_should_pull_no_image_not_present_locally(
            self, mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = False
        mock_search.return_value = None
        self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                          None, 'nonexisting', 'tag', 'never')

    @mock.patch.object(driver.GlanceDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_should_pull_no_image_present_locally(
            self, mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = False
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        self.assertEqual({'image': 'nginx', 'path': 'xyz'},
                         self.driver.pull_image(None, 'nonexisting',
                                                'tag', 'never'))

    @mock.patch('zun.image.glance.utils.create_glanceclient')
    @mock.patch.object(driver.GlanceDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_failure(self, mock_should_pull_image,
                                mock_search, mock_glance):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_glance.side_effect = Exception
        self.assertRaises(exception.ZunException, self.driver.pull_image,
                          None, 'nonexisting', 'tag', 'always')

    @mock.patch.object(driver.GlanceDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    @mock.patch('zun.image.glance.utils.create_glanceclient')
    @mock.patch('zun.image.glance.utils.find_image')
    def test_pull_image(self, mock_find_image, mock_glance,
                        mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_glance.images.data = mock.MagicMock(return_value='content')
        image_meta = mock.MagicMock()
        image_meta.id = '1234'
        mock_find_image.return_value = image_meta
        CONF.set_override('images_directory', self.test_dir, group='glance')
        out_path = os.path.join(self.test_dir, '1234' + '.tar')
        ret = self.driver.pull_image(None, 'image', 'latest', 'always')
        self.assertEqual({'image': 'image', 'path': out_path}, ret)
        self.assertTrue(os.path.isfile(ret['path']))

    @mock.patch('zun.image.glance.utils.create_glanceclient')
    @mock.patch.object(driver.GlanceDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_not_found(self, mock_should_pull_image,
                                  mock_search, mock_glance):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        with mock.patch('zun.image.glance.utils.find_image') as mock_find:
            mock_find.side_effect = exception.ImageNotFound
            self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                              None, 'nonexisting', 'tag', 'always')
