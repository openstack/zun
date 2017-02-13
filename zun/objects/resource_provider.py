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


@base.ZunObjectRegistry.register
class ResourceProvider(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(read_only=True),
        'uuid': fields.UUIDField(nullable=False),
        'name': fields.StringField(nullable=False),
        'root_provider': fields.UUIDField(nullable=False),
        'parent_provider': fields.UUIDField(nullable=True),
        'can_host': fields.IntegerField(default=0),
    }

    @staticmethod
    def _from_db_object(provider, db_provider):
        """Converts a database entity to a formal object."""
        for field in provider.fields:
            setattr(provider, field, db_provider[field])

        provider.obj_reset_changes()
        return provider

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ResourceProvider._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a resource provider based on uuid.

        :param uuid: the uuid of a resource provider.
        :param context: Security context
        :returns: a :class:`ResourceProvider` object.
        """
        db_provider = dbapi.get_resource_provider(context, uuid)
        provider = ResourceProvider._from_db_object(cls(context), db_provider)
        return provider

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a resource provider based on name.

        :param name: the logical name of a resource provider.
        :param context: Security context
        :returns: a :class:`ResourceProvider` object.
        """
        db_provider = dbapi.get_resource_provider(context, name)
        provider = ResourceProvider._from_db_object(cls(context), db_provider)
        return provider

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of ResourceProvider objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list resource providers.
        :returns: a list of :class:`ResourceProvider` object.

        """
        db_providers = dbapi.list_resource_providers(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return ResourceProvider._from_db_object_list(
            db_providers, cls, context)

    @base.remotable
    def create(self, context):
        """Create a ResourceProvider record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceProvider(context)

        """
        values = self.obj_get_changes()
        db_provider = dbapi.create_resource_provider(context, values)
        self._from_db_object(self, db_provider)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ResourceProvider from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceProvider(context)
        """
        dbapi.destroy_resource_provider(context, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ResourceProvider.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceProvider(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_resource_provider(context, self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this ResourceProvider.

        Loads a resource provider with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded resource provider column by column, if there are any
        updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ResourceProvider(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
