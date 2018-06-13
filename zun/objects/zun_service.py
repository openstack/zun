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
class ZunService(base.ZunPersistentObject, base.ZunObject):

    # Version 1.0: Initial version
    # Version 1.1: Add update method
    # Version 1.2: Add availability_zone field
    VERSION = '1.2'

    fields = {
        'id': fields.IntegerField(),
        'host': fields.StringField(nullable=True),
        'binary': fields.StringField(nullable=True),
        'disabled': fields.BooleanField(),
        'disabled_reason': fields.StringField(nullable=True),
        'last_seen_up': fields.DateTimeField(nullable=True,
                                             tzinfo_aware=False),
        'forced_down': fields.BooleanField(),
        'report_count': fields.IntegerField(),
        'availability_zone': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(zun_service, db_zun_service):
        """Converts a database entity to a formal object."""
        for field in zun_service.fields:
            setattr(zun_service, field, db_zun_service[field])

        zun_service.obj_reset_changes()
        return zun_service

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ZunService._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_host_and_binary(cls, context, host, binary):
        """Find a zun_service based on its hostname and binary.

        :param host: The host on which the binary is running.
        :param binary: The name of the binary.
        :param context: Security context.
        :returns: a :class:`ZunService` object.
        """
        db_zun_service = dbapi.get_zun_service(
            context, host, binary)
        if db_zun_service is None:
            return None
        zun_service = ZunService._from_db_object(
            cls(context), db_zun_service)
        return zun_service

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of ZunService objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ZunService` object.

        """
        db_zun_services = dbapi.list_zun_services(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir)
        return ZunService._from_db_object_list(db_zun_services, cls,
                                               context)

    @base.remotable_classmethod
    def list_by_binary(cls, context, binary):
        db_zun_services = dbapi.list_zun_services_by_binary(
            context, binary)
        return ZunService._from_db_object_list(db_zun_services, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a ZunService record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ZunService(context)
        """
        values = self.obj_get_changes()
        db_zun_service = dbapi.create_zun_service(values)
        self._from_db_object(self, db_zun_service)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ZunService from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ZunService(context)
        """
        dbapi.destroy_zun_service(self.host, self.binary)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ZunService.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ZunService(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_zun_service(self.host, self.binary, updates)
        self.obj_reset_changes()

    @base.remotable
    def report_state_up(self, context=None):
        """Touching the zun_service record to show aliveness.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ZunService(context)
        """
        self.report_count += 1
        self.save()

    @base.remotable
    def update(self, context, kwargs):
        """Update the ZunService, then save it.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ZunService(context)
        """
        if 'disabled' in kwargs:
            self.disabled = kwargs['disabled']
        if 'disabled_reason' in kwargs:
            self.disabled_reason = kwargs['disabled_reason']
        if 'forced_down' in kwargs:
            self.forced_down = kwargs['forced_down']
        self.save()
