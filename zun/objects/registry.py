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

from zun.db import api as dbapi
from zun.objects import base


LOG = logging.getLogger(__name__)


@base.ZunObjectRegistry.register
class Registry(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'domain': fields.StringField(nullable=True),
        'username': fields.StringField(nullable=True),
        'password': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(registry, db_registry):
        """Converts a database entity to a formal object."""
        for field in registry.fields:
            setattr(registry, field, db_registry[field])

        registry.obj_reset_changes()
        return registry

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Registry._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        """Find a registry based on id and return a :class:`Registry` object.

        :param id: the id of a registry.
        :param context: Security context
        :returns: a :class:`Registry` object.
        """
        db_registry = dbapi.get_registry_by_id(context, id)
        registry = Registry._from_db_object(cls(context), db_registry)
        return registry

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a registry based on uuid and return a :class:`Registry` object.

        :param uuid: the uuid of a registry.
        :param context: Security context
        :returns: a :class:`Registry` object.
        """
        db_registry = dbapi.get_registry_by_uuid(context, uuid)
        registry = Registry._from_db_object(cls(context), db_registry)
        return registry

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a registry based on name and return a Registry object.

        :param name: the logical name of a registry.
        :param context: Security context
        :returns: a :class:`Registry` object.
        """
        db_registry = dbapi.get_registry_by_name(context, name)
        registry = Registry._from_db_object(cls(context), db_registry)
        return registry

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Registry objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list registries.
        :returns: a list of :class:`Registry` object.

        """
        db_registries = dbapi.list_registries(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return Registry._from_db_object_list(db_registries, cls, context)

    @base.remotable
    def create(self, context):
        """Create a Registry record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Registry(context)

        """
        values = self.obj_get_changes()
        db_registry = dbapi.create_registry(context, values)
        self._from_db_object(self, db_registry)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Registry from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Registry(context)
        """
        dbapi.destroy_registry(context, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Registry.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Registry(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_registry(context, self.uuid, updates)

        self.obj_reset_changes()
