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
from mock import patch
import pecan

from zun.common import exception
from zun.common import utils
from zun.common.utils import check_container_id
from zun.common.utils import translate_exception
from zun import objects
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

        params = ({"kind": "capsule", "spec": {
            "containers": [{"image": "test1"}], "restartPolicy": "Always",
        }})
        spec_content, tpl_json = utils.check_capsule_template(params)
        self.assertEqual(spec_content["restart_policy"], "always")

    def test_check_capsule_template_unicode(self):
        with self.assertRaisesRegex(
            exception.InvalidCapsuleTemplate, "kind fields need to "
                                              "be set as capsule or Capsule"):
            params = (u'{"kind": "test", "spec": {"containers": []}}')
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "No Spec found"):
            params = (u'{"kind": "capsule"}')
            utils.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "No valid containers field"):
            params = (u'{"kind": "capsule", "spec": {}}')
            utils.check_capsule_template(params)

        params = (u'{"kind": "capsule", "spec": {'
                  u'"containers": [{"image": "test1"}],'
                  u'"restartPolicy": "Always"}}')
        spec_content, tpl_json = utils.check_capsule_template(params)
        self.assertEqual(spec_content["restart_policy"], "always")

    def test_capsule_get_container_spec(self):
        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "Capsule need to have one container at least"):
            params = ({"containers": []})
            utils.capsule_get_container_spec(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Container "
                                                  "image is needed"):
            params = ({"containers": [{"labels": {"app": "web"}}]})
            utils.capsule_get_container_spec(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Container image is needed"):
            params = ({"containers": [
                {"image": "test1"},
                {"environment": {"ROOT_PASSWORD": "foo0"}}]})
            utils.capsule_get_container_spec(params)

        params = ({"containers": [
            {"image": "test1", "env": {"ROOT_PASSWORD": "foo0"}}]})
        utils.capsule_get_container_spec(params)
        self.assertEqual(params.get("containers")[0].get("environment"),
                         {"ROOT_PASSWORD": "foo0"})
        self.assertNotIn("env", params.get("containers"))

    def test_capsule_get_volume_spec(self):
        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "Volume name is needed"):
            params = ({"volumes": [{"foo": "bar"}]})
            utils.capsule_get_volume_spec(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Volume size is needed"):
            params = ({"volumes": [{"name": "test",
                                    "cinder": {"foo": "bar"}}]})
            utils.capsule_get_volume_spec(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Volume size and uuid "
                                                  "could not be set at "
                                                  "the same time"):
            params = ({"volumes": [{"name": "test",
                                    "cinder": {"size": 3,
                                               "volumeID": "fakevolid"}}]})
            utils.capsule_get_volume_spec(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "Zun now Only support "
                                                  "Cinder volume driver"):
            params = ({"volumes": [{"name": "test", "other": {}}]})
            utils.capsule_get_volume_spec(params)

    @patch('zun.objects.Image.get_by_uuid')
    def test_get_image(self, mock_image_get_by_uuid):
        test_image = db_utils.get_test_image()
        test_image_obj = objects.Image(self.context, **test_image)
        mock_image_get_by_uuid.return_value = test_image_obj
        with mock.patch.object(pecan, 'request'):
            image = utils.get_image(test_image['uuid'])
            mock_image_get_by_uuid.assert_called_once_with(
                mock.ANY,
                test_image['uuid'])
            self.assertEqual(test_image['uuid'], image.uuid)

    @mock.patch.object(objects.ContainerActionEvent, 'event_start')
    @mock.patch.object(objects.ContainerActionEvent, 'event_finish')
    def test_wart_container_event(self, mock_finish, mock_start):
        container = Container(self.context, **db_utils.get_test_container())

        @utils.wrap_container_event(prefix='compute')
        def fake_event(self, context, container):
            pass

        fake_event(self, self.context, container=container)

        self.assertTrue(mock_start.called)
        self.assertTrue(mock_finish.called)

    @mock.patch.object(objects.ContainerActionEvent, 'event_start')
    @mock.patch.object(objects.ContainerActionEvent, 'event_finish')
    def test_wrap_container_event_return(self, mock_finish, mock_start):
        container = Container(self.context, **db_utils.get_test_container())

        @utils.wrap_container_event(prefix='compute')
        def fake_event(self, context, container):
            return True

        retval = fake_event(self, self.context, container=container)

        self.assertTrue(retval)
        self.assertTrue(mock_start.called)
        self.assertTrue(mock_finish.called)

    @mock.patch.object(objects.ContainerActionEvent, 'event_start')
    @mock.patch.object(objects.ContainerActionEvent, 'event_finish')
    def test_wrap_conatiner_event_log_exception(self, mock_finish, mock_start):
        container = Container(self.context, **db_utils.get_test_container())

        @utils.wrap_container_event(prefix='compute')
        def fake_event(self, context, container):
            raise exception.ZunException()

        self.assertRaises(exception.ZunException, fake_event,
                          self, self.context, container=container)

        self.assertTrue(mock_start.called)
        self.assertTrue(mock_finish.called)
        args, kwargs = mock_finish.call_args
        self.assertIsInstance(kwargs['exc_val'], exception.ZunException)
