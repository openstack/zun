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

from oslo_utils import fixture as utils_fixture
from oslo_utils import timeutils

from testtools.matchers import HasLength

from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

NOW = timeutils.utcnow().replace(microsecond=0)


class TestContainerActionObject(base.DbTestCase):

    def setUp(self):
        super(TestContainerActionObject, self).setUp()
        self.fake_action = utils.get_test_action()

    def test_get_by_request_id(self):
        container_ident = self.fake_action['container_uuid']
        request_id = self.fake_action['request_id']
        with mock.patch.object(self.dbapi, 'action_get_by_request_id',
                               autospec=True) as mock_get_action:
            mock_get_action.return_value = self.fake_action
            action = objects.ContainerAction.get_by_request_id(
                self.context, container_ident, request_id)
            mock_get_action.assert_called_once_with(
                self.context, container_ident, request_id)
            self.assertEqual(self.context, action._context)

    def test_get_by_container_uuid(self):
        container_ident = self.fake_action['container_uuid']
        with mock.patch.object(self.dbapi, 'actions_get', autospec=True) \
            as mock_get_actions:
            mock_get_actions.return_value = [self.fake_action]
            actions = objects.ContainerAction.get_by_container_uuid(
                self.context, container_ident)
            mock_get_actions.assert_called_once_with(self.context,
                                                     container_ident)

            self.assertThat(actions, HasLength(1))
            self.assertIsInstance(actions[0], objects.ContainerAction)
            self.assertEqual(self.context, actions[0]._context)

    def test_action_start(self):
        self.useFixture(utils_fixture.TimeFixture(NOW))
        container_ident = self.fake_action['container_uuid']
        action_name = self.fake_action['action']
        test_class = objects.ContainerAction
        expected_packed_values = test_class.pack_action_start(
            self.context, container_ident, action_name)
        with mock.patch.object(self.dbapi, 'action_start', autospec=True) \
            as mock_action_start:
            mock_action_start.return_value = self.fake_action
            action = objects.ContainerAction.action_start(
                self.context, container_ident, action_name, want_result=True)
            mock_action_start.assert_called_once_with(
                self.context, expected_packed_values)
            self.assertEqual(self.context, action._context)


class TestContainerActionEventObject(base.DbTestCase):

    def setUp(self):
        super(TestContainerActionEventObject, self).setUp()
        self.fake_action = utils.get_test_action()
        self.fake_event = utils.get_test_action_event()

    def test_get_by_action(self):
        action_id = self.fake_event['action_id']
        with mock.patch.object(self.dbapi, 'action_events_get',
                               autospec=True) as mock_get_event:
            mock_get_event.return_value = [self.fake_event]
            events = objects.ContainerActionEvent.get_by_action(self.context,
                                                                action_id)
            mock_get_event.assert_called_once_with(self.context, action_id)
            self.assertThat(events, HasLength(1))
            self.assertIsInstance(events[0], objects.ContainerActionEvent)
            self.assertEqual(self.context, events[0]._context)

    def test_event_start(self):
        self.useFixture(utils_fixture.TimeFixture(NOW))
        container_uuid = self.fake_action['container_uuid']
        event_name = self.fake_event['event']
        test_class = objects.ContainerActionEvent
        expected_packed_values = test_class.pack_action_event_start(
            self.context, container_uuid, event_name)
        with mock.patch.object(self.dbapi, 'action_event_start',
                               autospec=True) as mock_event_start:
            mock_event_start.return_value = self.fake_event
            event = objects.ContainerActionEvent.event_start(
                self.context, container_uuid, event_name, want_result=True)
            mock_event_start.assert_called_once_with(self.context,
                                                     expected_packed_values)
            self.assertEqual(self.context, event._context)

    def test_event_finish(self):
        self.useFixture(utils_fixture.TimeFixture(NOW))
        container_uuid = self.fake_action['container_uuid']
        event_name = self.fake_event['event']
        test_class = objects.ContainerActionEvent
        expected_packed_values = test_class.pack_action_event_finish(
            self.context, container_uuid, event_name)
        with mock.patch.object(self.dbapi, 'action_event_finish',
                               autospec=True) as mock_event_finish:
            mock_event_finish.return_value = self.fake_event
            event = objects.ContainerActionEvent.event_finish(
                self.context, container_uuid, event_name, want_result=True)
            mock_event_finish.assert_called_once_with(self.context,
                                                      expected_packed_values)
            self.assertEqual(self.context, event._context)
