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

    @mock.patch('zun.common.clients.OpenStackClients.neutron')
    def test_list_ports(self, mock_neutron_client):
        container = Container(self.context, **db_utils.get_test_container())
        container.addresses = None
        self.assertEqual([], utils.list_ports(self.context, container))
        container.addresses = {'df1e72a0-0251': [
            {'version': 4,
             'addr': '172.24.4.13',
             'port': '2a3fcf1'}]}
        neutron_client_instance = mock.MagicMock()
        neutron_client_instance.show_port.return_value = \
            {'port': 'test_port_info'}
        mock_neutron_client.return_value = neutron_client_instance
        result_container_ports = utils.list_ports(self.context, container)
        self.assertEqual(['test_port_info'], result_container_ports)

    @mock.patch('zun.common.clients.OpenStackClients.neutron')
    def test_get_security_group_ids(self, mock_neutron_client):
        security_groups = None
        self.assertIsNone(utils.get_security_group_ids(self.context,
                                                       security_groups))
        security_groups = ['test_security_group_name']
        neutron_client_instance = mock.MagicMock()
        neutron_client_instance.list_security_groups.return_value = \
            {'security_groups': [{'id': 'test_security_group_id',
                                 'name': 'test_security_group_name'}]}
        mock_neutron_client.return_value = neutron_client_instance
        security_group_ids = utils.get_security_group_ids(self.context,
                                                          security_groups)
        self.assertEqual(['test_security_group_id'], security_group_ids)
        security_groups = ["not_attached_security_group_name"]
        self.assertRaises(exception.ZunException, utils.get_security_group_ids,
                          self.context, security_groups)

    def test_check_capsule_template(self):
        with self.assertRaisesRegex(
            exception.InvalidCapsuleTemplate, "kind fields need to "
                                              "be set as capsule or Capsule"):
            params = ({"kind": "test", "spec": {"containers": []}})
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "No Spec found"):
            params = ({"kind": "capsule"})
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "No valid containers field"):
            params = ({"kind": "capsule", "spec": {}})
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "Capsule need to have one container at least"):
            params = ({"kind": "capsule", "spec": {"containers": []}})
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Container "
                                                  "image is needed"):
            params = ({"kind": "capsule",
                       "spec": {"containers": [{"labels": {"app": "web"}}]}})
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Container image is needed"):
            params = ({"kind": "capsule",
                       "spec": {"containers": [{"image": "test1"},
                                {"environment": {"ROOT_PASSWORD": "foo0"}}]}})
            utils.check_capsule_template(params)
