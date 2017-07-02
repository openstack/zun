#    Copyright 2016 IBM, Corp.
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

from zun.common import exception
from zun.common import utils
from zun.common.utils import check_container_id
from zun.common.utils import translate_exception
from zun.objects.container import Container
from zun.tests import base
from zun.tests.unit.db import utils as db_utils


class TestUtils(base.TestCase):
    """Test cases for zun.common.utils"""

    def test_check_container_id(self):

        @check_container_id
        def foo(self, context, container):
            pass

        fake_container = mock.MagicMock()
        fake_container.container_id = None

        self.assertRaises(exception.Invalid, foo,
                          self, self.context, fake_container)

    def test_translate_exception(self):

        @translate_exception
        def foo(self, context):
            raise TypeError()

        self.assertRaises(exception.ZunException, foo,
                          self, mock.MagicMock())

    def test_parse_image_name(self):
        self.assertEqual(('test', 'latest'),
                         utils.parse_image_name('test:latest'))
        self.assertEqual(('test', 'latest'),
                         utils.parse_image_name('test'))
        self.assertEqual(('test', 'test'),
                         utils.parse_image_name('test:test'))
        self.assertEqual(('test-test', 'test'),
                         utils.parse_image_name('test-test:test'))

    def test_get_image_pull_policy(self):
        self.assertEqual('always',
                         utils.get_image_pull_policy('always',
                                                     'latest'))
        self.assertEqual('always',
                         utils.get_image_pull_policy(None,
                                                     'latest'))
        self.assertEqual('ifnotpresent',
                         utils.get_image_pull_policy(None,
                                                     '2.0'))

    def test_should_pull_image(self):
        self.assertFalse(utils.should_pull_image('never', True))
        self.assertFalse(utils.should_pull_image('never', False))
        self.assertTrue(utils.should_pull_image('always', True))
        self.assertTrue(utils.should_pull_image('always', False))
        self.assertTrue(utils.should_pull_image('ifnotpresent', False))
        self.assertFalse(utils.should_pull_image('ifnotpresent', True))

    def test_validate_container_state(self):
        container = Container(self.context, **db_utils.get_test_container())
        container.status = 'Stopped'
        with self.assertRaisesRegex(exception.InvalidStateException,
                                    "%s" % container.uuid):
            utils.validate_container_state(container, 'stop')
        with self.assertRaisesRegex(exception.InvalidStateException,
                                    "%s" % container.uuid):
            utils.validate_container_state(container, 'pause')
        container.status = 'Running'
        with self.assertRaisesRegex(exception.InvalidStateException,
                                    "%s" % container.uuid):
            utils.validate_container_state(container, 'start')
        with self.assertRaisesRegex(exception.InvalidStateException,
                                    "%s" % container.uuid):
            utils.validate_container_state(container, 'unpause')
        with self.assertRaisesRegex(exception.InvalidStateException,
                                    "%s" % container.uuid):
            utils.validate_container_state(container, 'delete')
        self.assertIsNone(utils.validate_container_state(
            container, 'reboot'))
        container.status = 'Stopped'
        self.assertIsNone(utils.validate_container_state(
            container, 'reboot'))
        container.status = 'Running'
        self.assertIsNone(utils.validate_container_state(
            container, 'execute'))
