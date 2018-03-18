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
from zun.image.docker import driver as docker_driver
from zun.image import driver
from zun.image.glance import driver as glance_driver
from zun.tests import base

CONF = zun.conf.CONF


class TestDriver(base.BaseTestCase):
    def setUp(self):
        super(TestDriver, self).setUp()

    def test_load_image_driver_failure(self):
        CONF.set_override('default_image_driver', None)
        self.assertRaises(SystemExit, driver.load_image_driver)
        self.assertRaises(SystemExit, driver.load_image_driver,
                          'UnknownDriver')

    def test_load_image_driver(self):
        image_driver = driver.load_image_driver()
        self.assertIsInstance(image_driver, docker_driver.DockerDriver)

        CONF.set_override('images_directory', None, group='glance')
        image_driver = driver.load_image_driver('glance')
        self.assertIsInstance(image_driver, glance_driver.GlanceDriver)
