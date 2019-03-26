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
from zun.objects import volume as volume_obj


LOG = logging.getLogger(__name__)


_VOLUME_MAPPING_OPTIONAL_JOINED_FIELDS = [
    'container',
    'volume',
]
VOLUME_ATTRS = [
    'volume_provider',
    'cinder_volume_id',
    'connection_info',
    'auto_remove',
    'host',
    'contents',
]
VOLUME_MAPPING_OPTIONAL_ATTRS = \
    _VOLUME_MAPPING_OPTIONAL_JOINED_FIELDS + VOLUME_ATTRS


def _expected_cols(expected_attrs):
    return [attr for attr in expected_attrs
            if attr in _VOLUME_MAPPING_OPTIONAL_JOINED_FIELDS]


@base.ZunObjectRegistry.register
class VolumeMapping(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add field "auto_remove"
    # Version 1.2: Add field "host"
    # Version 1.3: Add field "contents"
    # Version 1.4: Rename field "volume_id" to "cinder_volume_id"
    # Version 1.5: Add method "count"
    VERSION = '1.5'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=False),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'cinder_volume_id': fields.UUIDField(nullable=True),
        'volume_provider': fields.StringField(nullable=False),
        'container_path': fields.StringField(nullable=True),
        'container_uuid': fields.UUIDField(nullable=True),
        'container': fields.ObjectField('ContainerBase', nullable=True),
        'connection_info': fields.SensitiveStringField(nullable=True),
        'auto_remove': fields.BooleanField(nullable=True),
        'host': fields.StringField(nullable=True),
        'contents': fields.SensitiveStringField(nullable=True),
        'volume_id': fields.IntegerField(nullable=False),
        'volume': fields.ObjectField('Volume', nullable=True),
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

    @base.remotable_classmethod
    def list_by_cinder_volume(cls, context, cinder_volume_id):
        filters = {'cinder_volume_id': cinder_volume_id}
        db_volumes = dbapi.list_volume_mappings(context, filters=filters)
        return VolumeMapping._from_db_object_list(db_volumes, cls, context)

    @base.remotable_classmethod
    def count(cls, context, **filters):
        return dbapi.count_volume_mappings(context, **filters)

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
        if 'volume' in values:
            raise exception.ObjectActionError(action='create',
                                              reason='volume assigned')

        self._create_volume(context, values)
        db_volume = dbapi.create_volume_mapping(context, values)
        self._from_db_object(self, db_volume)

    def _create_volume(self, context, values):
        volume_values = {}
        for attrname in list(values.keys()):
            if attrname in VOLUME_ATTRS:
                volume_values[attrname] = values.pop(attrname)
        volume_values['user_id'] = values['user_id']
        volume_values['project_id'] = values['project_id']
        if 'volume_id' not in values:
            volume = volume_obj.Volume(context, **volume_values)
            volume.create(context)
            values['volume_id'] = volume.id

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
        context = context or self._context
        if not self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='already destroyed')
        dbapi.destroy_volume_mapping(context, self.uuid)
        self._destroy_volume(context)
        delattr(self, 'id')
        self.obj_reset_changes()

    def _destroy_volume(self, context):
        if VolumeMapping.count(context,
                               volume_id=self.volume_id) == 0:
            dbapi.destroy_volume(context, self.volume_id)

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
        if 'volume' in updates:
            raise exception.ObjectActionError(action='save',
                                              reason='volume changed')
        updates.pop('id', None)
        self._update_volume(context, updates)
        dbapi.update_volume_mapping(context, self.uuid, updates)

        self.obj_reset_changes()

    def _update_volume(self, context, values):
        volume = self.volume
        for attrname in list(values.keys()):
            if attrname in VOLUME_ATTRS:
                setattr(volume, attrname, values.pop(attrname))
        volume.save(context)

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
            if not self.obj_attr_is_set(field):
                continue
            if field == 'volume':
                self.volume.refresh()
            elif field == 'container':
                self.container.refresh()
            elif getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
        self.obj_reset_changes()

    def obj_load_attr(self, attrname):
        if attrname not in VOLUME_MAPPING_OPTIONAL_ATTRS:
            raise exception.ObjectActionError(
                action='obj_load_attr',
                reason='attribute %s not lazy-loadable' % attrname)
        if not self._context:
            raise exception.OrphanedObjectError(method='obj_load_attr',
                                                objtype=self.obj_name())

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   })

        if attrname in VOLUME_ATTRS:
            value = getattr(self.volume, attrname)
            setattr(self, attrname, value)
            self.obj_reset_changes(fields=[attrname])
        if attrname == 'container':
            self.container = container.ContainerBase.get_container_any_type(
                self._context, self.container_uuid)
            self.obj_reset_changes(fields=['container'])
        if attrname == 'volume':
            self.volume = volume_obj.Volume.get_by_id(self._context,
                                                      self.volume_id)
            self.obj_reset_changes(fields=['volume'])
