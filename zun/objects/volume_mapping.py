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
from zun.objects import container


LOG = logging.getLogger(__name__)


_VOLUME_MAPPING_OPTIONAL_JOINED_FIELD = ['container']
VOLUME_MAPPING_OPTIONAL_ATTRS = _VOLUME_MAPPING_OPTIONAL_JOINED_FIELD


def _expected_cols(expected_attrs):
    return [attr for attr in expected_attrs
            if attr in _VOLUME_MAPPING_OPTIONAL_JOINED_FIELD]


@base.ZunObjectRegistry.register
class VolumeMapping(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add field "auto_remove"
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=False),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'volume_id': fields.UUIDField(nullable=False),
        'volume_provider': fields.StringField(nullable=False),
        'container_path': fields.StringField(nullable=True),
        'container_uuid': fields.UUIDField(nullable=True),
        'container': fields.ObjectField('Container', nullable=True),
        'connection_info': fields.SensitiveStringField(nullable=True),
        'auto_remove': fields.BooleanField(nullable=True),
    }

    @staticmethod
    def _from_db_object(volume, db_volume):
        """Converts a database entity to a formal object."""
        for field in volume.fields:
            if field in VOLUME_MAPPING_OPTIONAL_ATTRS:
                continue
            setattr(volume, field, db_volume[field])

        volume.obj_reset_changes()
        return volume

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [VolumeMapping._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a volume mapping based on uuid.

        :param uuid: the uuid of a volume mapping.
        :param context: Security context
        :returns: a :class:`VolumeMapping` object.
        """
        db_volume = dbapi.get_volume_mapping_by_uuid(context, uuid)
        volume = VolumeMapping._from_db_object(cls(context), db_volume)
        return volume

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of VolumeMapping objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list volume mappings.
        :returns: a list of :class:`VolumeMapping` object.

        """
        db_volumes = dbapi.list_volume_mappings(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return VolumeMapping._from_db_object_list(db_volumes, cls, context)

    @base.remotable_classmethod
    def list_by_container(cls, context, container_uuid):
        filters = {'container_uuid': container_uuid}
        db_volumes = dbapi.list_volume_mappings(context, filters=filters)
        return VolumeMapping._from_db_object_list(db_volumes, cls, context)

    @base.remotable
    def create(self, context):
        """Create a VolumeMapping record in the DB.

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
        if 'container' in values:
            raise exception.ObjectActionError(action='create',
                                              reason='container assigned')

        db_volume = dbapi.create_volume_mapping(context, values)
        self._from_db_object(self, db_volume)

    @base.remotable
    def destroy(self, context=None):
        """Delete the VolumeMapping from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object.
        """
        if not self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='already destroyed')
        dbapi.destroy_volume_mapping(context, self.uuid)
        delattr(self, 'id')
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this VolumeMapping.

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
        dbapi.update_volume_mapping(context, self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this VolumeMapping.

        Loads a volume mapping with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded volume mapping column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object.
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))

    def obj_load_attr(self, attrname):
        if attrname not in VOLUME_MAPPING_OPTIONAL_ATTRS:
            raise exception.ObjectActionError(
                action='obj_load_attr',
                reason='attribute %s not lazy-loadable' % attrname)
        if not self._context:
            raise exception.OrphanedObjectError(method='obj_load_attr',
                                                objtype=self.obj_name())

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s uuid %(uuid)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   'uuid': self.uuid,
                   })
        self.container = container.Container.get_by_uuid(self._context,
                                                         self.container_uuid)
        self.obj_reset_changes(fields=['container'])
