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

import traceback

from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_versionedobjects import fields
import six

from zun.db import api as dbapi
from zun.objects import base

LOG = logging.getLogger(__name__)


@base.ZunObjectRegistry.register
class ContainerAction(base.ZunPersistentObject, base.ZunObject):

    # Version 1.0: Initial version
    # Version 1.1: Add uuid column.
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'action': fields.StringField(nullable=True),
        'container_uuid': fields.UUIDField(nullable=True),
        'request_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'start_time': fields.DateTimeField(tzinfo_aware=False, nullable=True),
        'finish_time': fields.DateTimeField(tzinfo_aware=False, nullable=True),
        'message': fields.StringField(nullable=True),
        # NOTE: By now, this field is only used for etcd. If using sql,
        # this field will be None.
        'uuid': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, action, db_action):
        for field in action.fields:
            setattr(action, field, getattr(db_action, field, None))

        action.obj_reset_changes()
        return action

    @staticmethod
    def _from_db_object_list(context, cls, db_objects):
        """Converts a list of database entities to a list of formal objects."""
        return [ContainerAction._from_db_object(context, cls(context), obj)
                for obj in db_objects]

    @staticmethod
    def pack_action_start(context, container_uuid, action_name):
        values = {'request_id': context.request_id,
                  'container_uuid': container_uuid,
                  'user_id': context.user_id,
                  'project_id': context.project_id,
                  'action': action_name,
                  'start_time': context.timestamp}
        return values

    @staticmethod
    def pack_action_finish(context, container_uuid):
        values = {'request_id': context.request_id,
                  'container_uuid': container_uuid,
                  'finish_time': timeutils.utcnow()}
        return values

    @base.remotable_classmethod
    def get_by_request_id(cls, context, container_uuid, request_id):
        db_action = dbapi.action_get_by_request_id(context, container_uuid,
                                                   request_id)
        if db_action:
            return cls._from_db_object(context, cls(context), db_action)

    @base.remotable_classmethod
    def action_start(cls, context, container_uuid, action_name,
                     want_result=True):
        values = cls.pack_action_start(context, container_uuid, action_name)
        db_action = dbapi.action_start(context, values)
        if want_result:
            return cls._from_db_object(context, cls(context), db_action)

    @base.remotable_classmethod
    def get_by_container_uuid(cls, context, instance_uuid):
        db_actions = dbapi.actions_get(context, instance_uuid)
        return ContainerAction._from_db_object_list(context, cls, db_actions)


@base.ZunObjectRegistry.register
class ContainerActionEvent(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'id': fields.IntegerField(),
        'event': fields.StringField(nullable=True),
        'action_id': fields.IntegerField(nullable=True),
        'start_time': fields.DateTimeField(tzinfo_aware=False, nullable=True),
        'finish_time': fields.DateTimeField(tzinfo_aware=False, nullable=True),
        'result': fields.StringField(nullable=True),
        'traceback': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, event, db_event):
        for field in event.fields:
            setattr(event, field, db_event[field])

        event.obj_reset_changes()
        return event

    @staticmethod
    def _from_db_object_list(context, cls, db_objects):
        """Converts a list of database entities to a list of formal objects."""
        return [ContainerActionEvent._from_db_object(context, cls(context),
                                                     obj)
                for obj in db_objects]

    @staticmethod
    def pack_action_event_start(context, container_uuid, event_name):
        values = {'event': event_name,
                  'container_uuid': container_uuid,
                  'request_id': context.request_id,
                  'start_time': timeutils.utcnow()}
        return values

    @staticmethod
    def pack_action_event_finish(context, container_uuid, event_name,
                                 exc_val=None, exc_tb=None):
        values = {'event': event_name,
                  'container_uuid': container_uuid,
                  'request_id': context.request_id,
                  'finish_time': timeutils.utcnow()}
        if exc_tb is None:
            values['result'] = 'Success'
        else:
            values['result'] = 'Error'
            values['message'] = exc_val
            values['traceback'] = exc_tb
        return values

    @base.remotable_classmethod
    def event_start(cls, context, container_uuid, event_name,
                    want_result=True):
        values = cls.pack_action_event_start(context, container_uuid,
                                             event_name)
        db_event = dbapi.action_event_start(context, values)
        if want_result:
            return cls._from_db_object(context, cls(context), db_event)

    @base.remotable_classmethod
    def event_finish(cls, context, container_uuid, event_name, exc_val=None,
                     exc_tb=None, want_result=None):
        if exc_val:
            exc_val = six.text_type(exc_val)
        if exc_tb and not isinstance(exc_tb, six.string_types):
            exc_tb = ''.join(traceback.format_tb(exc_tb))
        values = cls.pack_action_event_finish(context, container_uuid,
                                              event_name, exc_val=exc_val,
                                              exc_tb=exc_tb)
        db_event = dbapi.action_event_finish(context, values)
        if want_result:
            return cls._from_db_object(context, cls(context), db_event)

    @base.remotable_classmethod
    def get_by_action(cls, context, action_id):
        db_events = dbapi.action_events_get(context, action_id)
        return ContainerActionEvent._from_db_object_list(context, cls,
                                                         db_events)
