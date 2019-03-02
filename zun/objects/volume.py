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

from oslo_log import log as logging
from oslo_versionedobjects import fields

from zun.common import exception
from zun.db import api as dbapi
from zun.objects import base


LOG = logging.getLogger(__name__)


@base.ZunObjectRegistry.register
class Volume(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=False),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'cinder_volume_id': fields.UUIDField(nullable=True),
        'volume_provider': fields.StringField(nullable=False),
        'connection_info': fields.SensitiveStringField(nullable=True),
        'auto_remove': fields.BooleanField(nullable=True),
        'host': fields.StringField(nullable=True),
        'contents': fields.SensitiveStringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(volume, db_volume):
        """Converts a database entity to a formal object."""
        for field in volume.fields:
            setattr(volume, field, db_volume[field])

        volume.obj_reset_changes()
        return volume

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Volume._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, vol_id):
        """Find a volume mapping based on uuid.

        :param uuid: the uuid of a volume mapping.
        :param context: Security context
        :returns: a :class:`Volume` object.
        """
        db_volume = dbapi.get_volume_by_id(context, vol_id)
        volume = Volume._from_db_object(cls(context), db_volume)
        return volume

    @base.remotable
    def create(self, context):
        """Create a Volume record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object.

        """
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')

        values = self.obj_get_changes()
        db_volume = dbapi.create_volume(context, values)
        self._from_db_object(self, db_volume)

    @base.remotable
    def save(self, context=None):
        """Save updates to this Volume.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object.
        """
        updates = self.obj_get_changes()
        if 'container' in updates:
            raise exception.ObjectActionError(action='save',
                                              reason='container changed')
        updates.pop('id', None)
        dbapi.update_volume(context, self.uuid, updates)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Volume.

        Loads a volume with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded volume column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object.
        """
        current = self.__class__.get_by_id(self._context, self.id)
        for field in self.fields:
            if not self.obj_attr_is_set(field):
                continue
            if getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
        self.obj_reset_changes()
