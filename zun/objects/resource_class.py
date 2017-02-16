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

from oslo_versionedobjects import fields

from zun.db import api as dbapi
from zun.objects import base
from zun.objects import fields as z_fields


@base.ZunObjectRegistry.register
class ResourceClass(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add uuid field
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(read_only=True),
        'uuid': fields.UUIDField(nullable=False),
        'name': z_fields.ResourceClassField(nullable=False),
    }

    @staticmethod
    def _from_db_object(resource, db_resource):
        """Converts a database entity to a formal object."""
        for field in resource.fields:
            setattr(resource, field, db_resource[field])

        resource.obj_reset_changes()
        return resource

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ResourceClass._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a resource class based on uuid.

        :param uuid: the uuid of a resource class.
        :param context: Security context
        :returns: a :class:`ResourceClass` object.
        """
        db_resource = dbapi.get_resource_class(context, uuid)
        resource = ResourceClass._from_db_object(cls(context), db_resource)
        return resource

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a resource class based on name.

        :param name: the name of a resource class.
        :param context: Security context
        :returns: a :class:`ResourceClass` object.
        """
        db_resource = dbapi.get_resource_class(context, name)
        resource = ResourceClass._from_db_object(cls(context), db_resource)
        return resource

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None, sort_key=None,
             sort_dir=None):
        """Return a list of ResourceClass objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ResourceClass` object.

        """
        db_resources = dbapi.list_resource_classes(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir)
        return ResourceClass._from_db_object_list(
            db_resources, cls, context)

    @base.remotable
    def create(self, context):
        """Create a ResourceClass record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceClass(context)

        """
        values = self.obj_get_changes()
        db_resource = dbapi.create_resource_class(context, values)
        self._from_db_object(self, db_resource)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ResourceClass from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceClass(context)
        """
        dbapi.destroy_resource_class(context, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ResourceClass.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceClass(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_resource_class(context, self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this ResourceClass.

        Loads a resource class with the same id from the database and
        checks for updated attributes. Updates are applied from
        the loaded resource class column by column, if there are any
        updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceClass(context)
        """
        current = self.__class__.get_by_uuid(self._context, self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
