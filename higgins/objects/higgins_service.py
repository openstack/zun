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

from higgins.db import api as dbapi
from higgins.objects import base


@base.HigginsObjectRegistry.register
class HigginsService(base.HigginsPersistentObject, base.HigginsObject,
                     base.HigginsObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'host': fields.StringField(nullable=True),
        'binary': fields.StringField(nullable=True),
        'disabled': fields.BooleanField(),
        'disabled_reason': fields.StringField(nullable=True),
        'last_seen_up': fields.DateTimeField(nullable=True),
        'forced_down': fields.BooleanField(),
        'report_count': fields.IntegerField(),
    }

    @staticmethod
    def _from_db_object(higgins_service, db_higgins_service):
        """Converts a database entity to a formal object."""
        for field in higgins_service.fields:
            higgins_service[field] = db_higgins_service[field]

        higgins_service.obj_reset_changes()
        return higgins_service

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [HigginsService._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_host_and_binary(cls, context, host, binary):
        """Find a higgins_service based on its hostname and binary.

        :param host: The host on which the binary is running.
        :param binary: The name of the binary.
        :param context: Security context.
        :returns: a :class:`HigginsService` object.
        """
        db_higgins_service = cls.dbapi.get_higgins_service_by_host_and_binary(
            context, host, binary)
        if db_higgins_service is None:
            return None
        higgins_service = HigginsService._from_db_object(
            cls(context), db_higgins_service)
        return higgins_service

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of HigginsService objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`HigginsService` object.

        """
        db_higgins_services = cls.dbapi.get_higgins_service_list(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir)
        return HigginsService._from_db_object_list(db_higgins_services, cls,
                                                   context)

    @base.remotable
    def create(self, context=None):
        """Create a HigginsService record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: HigginsService(context)
        """
        values = self.obj_get_changes()
        db_higgins_service = self.dbapi.create_higgins_service(values)
        self._from_db_object(self, db_higgins_service)

    @base.remotable
    def destroy(self, context=None):
        """Delete the HigginsService from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: HigginsService(context)
        """
        self.dbapi.destroy_higgins_service(self.id)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this HigginsService.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: HigginsService(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_higgins_service(self.id, updates)
        self.obj_reset_changes()

    @base.remotable
    def report_state_up(self, context=None):
        """Touching the higgins_service record to show aliveness.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: HigginsService(context)
        """
        self.report_count += 1
        self.save()
