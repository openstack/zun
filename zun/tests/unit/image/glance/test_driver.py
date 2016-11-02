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

    @mock.patch('zun.image.glance.utils.create_glanceclient')
    def test_pull_image_failure(self, mock_glance):
        mock_glance.side_effect = Exception
        self.assertRaises(exception.ZunException, self.driver.pull_image,
                          None, 'nonexisting')

    @mock.patch('zun.image.glance.utils.create_glanceclient')
    def test_pull_image_not_found(self, mock_glance):
        with mock.patch('zun.image.glance.utils.find_image') as mock_find:
            mock_find.side_effect = exception.ImageNotFound
            self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                              None, 'nonexisting')

    @mock.patch('zun.image.glance.utils.create_glanceclient')
    @mock.patch('zun.image.glance.utils.find_image')
    def test_pull_image_found(self, mock_find_image, mock_glance):
        mock_glance.images.data = mock.MagicMock(return_value='content')
        image_meta = mock.MagicMock()
        image_meta.id = '1234'
        mock_find_image.return_value = image_meta
        CONF.set_override('images_directory', self.test_dir, group='glance')
        out_path = os.path.join(self.test_dir, '1234' + '.tar')
        ret = self.driver.pull_image(None, 'image')
        self.assertEqual(out_path, ret)
        self.assertTrue(os.path.isfile(ret))
