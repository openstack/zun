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

import zun.conf
from zun.image import driver
from zun.tests import base

CONF = zun.conf.CONF


class TestDriver(base.BaseTestCase):
    def setUp(self):
        super(TestDriver, self).setUp()

    def test_load_image_driver_failure(self):
        self.assertRaises(SystemExit, driver.load_image_driver)
        self.assertRaises(SystemExit, driver.load_image_driver,
                          'UnknownDriver')

    def test_load_image_driver(self):
        CONF.set_override('images_directory', None, group='glance')
        self.assertTrue(driver.load_image_driver, 'glance.GlanceDriver')
