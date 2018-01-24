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

"""Tests for manipulating Container Actions via the DB API"""
from datetime import datetime
from datetime import timedelta
import etcd
from etcd import Client as etcd_client
import mock
from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcdapi
from zun.db.etcd.api import EtcdAPI as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult

CONF = zun.conf.CONF


class _DBContainerActionBase(base.DbTestCase,
                             base.ModelsObjectComparatorMixin):

    IGNORED_FIELDS = [
        'id',
        'created_at',
        'updated_at',
        'details'
    ]

    def _create_action_values(self, uuid, action='create_container'):
        utils.create_test_container(context=self.context,
                                    name='cont1',
                                    uuid=uuid)

        values = {
            'action': action,
            'container_uuid': uuid,
            'request_id': self.context.request_id,
            'user_id': self.context.user_id,
            'project_id': self.context.project_id,
            'start_time': timeutils.utcnow(),
            'message': 'action-message'
        }
        return values

    def _create_event_values(self, uuid, event='do_create', extra=None):
        values = {
            'event': event,
            'container_uuid': uuid,
            'request_id': self.context.request_id,
            'start_time': timeutils.utcnow()
        }
        if extra is not None:
            values.update(extra)
        return values

    def _assertActionSaved(self, action, uuid):
        """Retrieve the action to ensure it was successfully added."""
        actions = dbapi.actions_get(self.context, uuid)
        self.assertEqual(1, len(actions))
        self._assertEqualObjects(action, actions[0])

    def _assertActionEventSaved(self, event, action_id):
        """Retrieve the event to ensure it was successfully added."""
        events = dbapi.action_events_get(self.context, action_id)
        self.assertEqual(1, len(events))
        self._assertEqualObjects(event, events[0],
                                 ['container_uuid', 'request_id'])


class DbContainerActionTestCase(_DBContainerActionBase):

    def setUp(self):
        super(DbContainerActionTestCase, self).setUp()

    def test_container_action_start(self):
        """Create a container action."""
        uuid = uuidutils.generate_uuid()
        action_values = self._create_action_values(uuid)
        action = dbapi.action_start(self.context, action_values)

        ignored_keys = self.IGNORED_FIELDS + ['finish_time']
        self._assertEqualObjects(action_values, action, ignored_keys)

        self._assertActionSaved(action, uuid)

    def test_container_actions_get_by_container(self):
        """Ensure we can get actions by UUID."""
        uuid1 = uuidutils.generate_uuid()

        expected = []

        action_values = self._create_action_values(uuid1)
        action = dbapi.action_start(self.context, action_values)
        expected.append(action)

        action_values['action'] = 'test-action'
        action = dbapi.action_start(self.context, action_values)
        expected.append(action)

        # Create an other container action.
        uuid2 = uuidutils.generate_uuid()
        action_values = self._create_action_values(uuid2, 'test-action')
        dbapi.action_start(self.context, action_values)

        actions = dbapi.actions_get(self.context, uuid1)
        self._assertEqualListsOfObjects(expected, actions)

    def test_container_action_get_by_container_and_request(self):
        """Ensure we can get an action by container UUID and request_id"""
        uuid1 = uuidutils.generate_uuid()

        action_values = self._create_action_values(uuid1)
        dbapi.action_start(self.context, action_values)
        request_id = action_values['request_id']

        # An other action using a different req id
        action_values['action'] = 'test-action'
        action_values['request_id'] = 'req-00000000-7522-4d99-7ff-111111111111'
        dbapi.action_start(self.context, action_values)

        action = dbapi.action_get_by_request_id(self.context, uuid1,
                                                request_id)
        self.assertEqual('create_container', action['action'])
        self.assertEqual(self.context.request_id, action['request_id'])

    def test_container_action_event_start(self):
        """Create a container action event."""
        uuid = uuidutils.generate_uuid()

        action_values = self._create_action_values(uuid)
        action = dbapi.action_start(self.context, action_values)

        event_values = self._create_event_values(uuid)
        event = dbapi.action_event_start(self.context, event_values)

        event_values['action_id'] = action['id']
        ignored_keys = self.IGNORED_FIELDS + ['finish_time', 'traceback',
                                              'result']
        self._assertEqualObjects(event_values, event, ignored_keys)

        self._assertActionEventSaved(event, action['id'])

    def test_container_action_event_start_without_action(self):
        uuid = uuidutils.generate_uuid()

        event_values = self._create_event_values(uuid)
        self.assertRaises(exception.ContainerActionNotFound,
                          dbapi.action_event_start, self.context, event_values)

    def test_container_action_event_finish_success(self):
        """Finish a container action event."""
        uuid = uuidutils.generate_uuid()

        action = dbapi.action_start(self.context,
                                    self._create_action_values(uuid))

        dbapi.action_event_start(self.context,
                                 self._create_event_values(uuid))

        event_values = {
            'finish_time': timeutils.utcnow() + timedelta(seconds=5),
            'result': 'Success'
        }

        event_values = self._create_event_values(uuid, extra=event_values)
        event = dbapi.action_event_finish(self.context, event_values)

        self._assertActionEventSaved(event, action['id'])
        action = dbapi.action_get_by_request_id(self.context, uuid,
                                                self.context.request_id)
        self.assertNotEqual('Error', action['message'])

    def test_container_action_event_finish_without_action(self):
        uuid = uuidutils.generate_uuid()

        event_values = {
            'finish_time': timeutils.utcnow() + timedelta(seconds=5),
            'result': 'Success'
        }
        event_values = self._create_event_values(uuid, extra=event_values)
        self.assertRaises(exception.ContainerActionNotFound,
                          dbapi.action_event_finish,
                          self.context, event_values)

    def test_container_action_events_get_in_order(self):
        """Ensure retrived action events are in order."""
        uuid1 = uuidutils.generate_uuid()

        action = dbapi.action_start(self.context,
                                    self._create_action_values(uuid1))

        extra1 = {
            'created_at': timeutils.utcnow()
        }

        extra2 = {
            'created_at': timeutils.utcnow() + timedelta(seconds=5)
        }

        event_val1 = self._create_event_values(uuid1, 'fake1', extra=extra1)
        event_val2 = self._create_event_values(uuid1, 'fake2', extra=extra1)
        event_val3 = self._create_event_values(uuid1, 'fake3', extra=extra2)

        event1 = dbapi.action_event_start(self.context, event_val1)
        event2 = dbapi.action_event_start(self.context, event_val2)
        event3 = dbapi.action_event_start(self.context, event_val3)

        events = dbapi.action_events_get(self.context, action['id'])

        self.assertEqual(3, len(events))

        self._assertEqualOrderedListOfObjects([event3, event2, event1], events,
                                              ['container_uuid', 'request_id'])


class EtcdDbContainerActionTestCase(_DBContainerActionBase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbContainerActionTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_container_action_start(self, mock_db_inst,
                                    mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid = uuidutils.generate_uuid()
        action_values = self._create_action_values(uuid)
        action = dbapi.action_start(self.context, action_values)

        ignored_keys = self.IGNORED_FIELDS + ['finish_time', 'uuid']

        self._assertEqualObjects(action_values, action.as_dict(), ignored_keys)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [action.as_dict()])
        action['start_time'] = datetime.isoformat(action['start_time'])
        self._assertActionSaved(action.as_dict(), uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_container_actions_get_by_container(self, mock_db_inst,
                                                mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid1 = uuidutils.generate_uuid()

        expected = []

        action_values = self._create_action_values(uuid1)
        action = dbapi.action_start(self.context, action_values)
        action['start_time'] = datetime.isoformat(action['start_time'])
        expected.append(action)

        action_values['action'] = 'test-action'
        action = dbapi.action_start(self.context, action_values)
        action['start_time'] = datetime.isoformat(action['start_time'])
        expected.append(action)

        # Create an other container action.
        uuid2 = uuidutils.generate_uuid()
        action_values = self._create_action_values(uuid2, 'test-action')
        dbapi.action_start(self.context, action_values)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            expected)
        actions = dbapi.actions_get(self.context, uuid1)
        self._assertEqualListsOfObjects(expected, actions)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_container_action_get_by_container_and_request(self, mock_write,
                                                           mock_read):
        """Ensure we can get an action by container UUID and request_id"""
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid1 = uuidutils.generate_uuid()

        action_values = self._create_action_values(uuid1)
        action = dbapi.action_start(self.context, action_values)
        request_id = action_values['request_id']

        # An other action using a different req id
        action_values['action'] = 'test-action'
        action_values['request_id'] = 'req-00000000-7522-4d99-7ff-111111111111'
        dbapi.action_start(self.context, action_values)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult([action])
        action = dbapi.action_get_by_request_id(self.context, uuid1,
                                                request_id)
        self.assertEqual('create_container', action['action'])
        self.assertEqual(self.context.request_id, action['request_id'])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, '_action_get_by_request_id')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_container_action_event_start(self, mock_db_inst,
                                          mock__action_get_by_request_id,
                                          mock_write, mock_read):
        """Create a container action event."""
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid = uuidutils.generate_uuid()

        action_values = self._create_action_values(uuid)
        action = dbapi.action_start(self.context, action_values)

        event_values = self._create_event_values(uuid)

        mock__action_get_by_request_id.return_value = action
        mock_read.side_effect = etcd.EtcdKeyNotFound
        event = dbapi.action_event_start(self.context, event_values)

        ignored_keys = self.IGNORED_FIELDS + ['finish_time', 'traceback',
                                              'result', 'action_uuid',
                                              'request_id', 'container_uuid',
                                              'uuid']
        self._assertEqualObjects(event_values, event, ignored_keys)

        event['start_time'] = datetime.isoformat(event['start_time'])
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult([event])
        self._assertActionEventSaved(event, action['uuid'])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_container_action_event_start_without_action(self, mock_write,
                                                         mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid = uuidutils.generate_uuid()

        event_values = self._create_event_values(uuid)
        self.assertRaises(exception.ContainerActionNotFound,
                          dbapi.action_event_start, self.context, event_values)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(etcd_api, '_action_get_by_request_id')
    @mock.patch.object(etcd_api, '_get_event_by_name')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_container_action_event_finish_success(
            self, mock_db_inst, mock_get_event_by_name,
            mock__action_get_by_request_id,
            mock_update, mock_write, mock_read):
        """Finish a container action event."""
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid = uuidutils.generate_uuid()

        action = dbapi.action_start(self.context,
                                    self._create_action_values(uuid))

        event_values = self._create_event_values(uuid)
        event_values['action_uuid'] = action['uuid']

        mock__action_get_by_request_id.return_value = action
        mock_read.side_effect = etcd.EtcdKeyNotFound
        event = dbapi.action_event_start(self.context, event_values)

        event_values = {
            'finish_time': timeutils.utcnow() + timedelta(seconds=5),
            'result': 'Success'
        }

        event_values = self._create_event_values(uuid, extra=event_values)

        mock__action_get_by_request_id.return_value = action
        mock_get_event_by_name.return_value = event
        mock_read.side_effect = lambda *args: FakeEtcdResult(event)
        event = dbapi.action_event_finish(self.context, event_values)

        event['start_time'] = datetime.isoformat(event['start_time'])
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult([event])
        self._assertActionEventSaved(event, action['uuid'])

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult([action])
        action = dbapi.action_get_by_request_id(self.context, uuid,
                                                self.context.request_id)
        self.assertNotEqual('Error', action['message'])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_container_action_event_finish_without_action(self, mock_write,
                                                          mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid = uuidutils.generate_uuid()

        event_values = {
            'finish_time': timeutils.utcnow() + timedelta(seconds=5),
            'result': 'Success'
        }
        event_values = self._create_event_values(uuid, extra=event_values)
        self.assertRaises(exception.ContainerActionNotFound,
                          dbapi.action_event_finish,
                          self.context, event_values)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, '_action_get_by_request_id')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_container_action_events_get_in_order(
            self, mock_db_inst, mock__action_get_by_request_id,
            mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        uuid1 = uuidutils.generate_uuid()

        action = dbapi.action_start(self.context,
                                    self._create_action_values(uuid1))

        extra1 = {
            'action_uuid': action['uuid'],
            'created_at': timeutils.utcnow()
        }

        extra2 = {
            'action_uuid': action['uuid'],
            'created_at': timeutils.utcnow() + timedelta(seconds=5)
        }

        event_val1 = self._create_event_values(uuid1, 'fake1', extra=extra1)
        event_val2 = self._create_event_values(uuid1, 'fake2', extra=extra1)
        event_val3 = self._create_event_values(uuid1, 'fake3', extra=extra2)

        mock__action_get_by_request_id.return_value = action
        mock_read.side_effect = etcd.EtcdKeyNotFound
        event1 = dbapi.action_event_start(self.context, event_val1)
        event1['start_time'] = datetime.isoformat(event1['start_time'])

        mock__action_get_by_request_id.return_value = action
        mock_read.side_effect = etcd.EtcdKeyNotFound
        event2 = dbapi.action_event_start(self.context, event_val2)
        event2['start_time'] = datetime.isoformat(event2['start_time'])

        mock__action_get_by_request_id.return_value = action
        mock_read.side_effect = etcd.EtcdKeyNotFound
        event3 = dbapi.action_event_start(self.context, event_val3)
        event3['start_time'] = datetime.isoformat(event3['start_time'])

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [event1, event2, event3])
        events = dbapi.action_events_get(self.context, action['uuid'])

        self.assertEqual(3, len(events))

        self._assertEqualOrderedListOfObjects([event3, event2, event1], events,
                                              ['container_uuid', 'request_id'])
