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
class Quota(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add uuid column
    # Version 1.2: Add destroy_all_by_project method
    VERSION = '1.2'

    fields = {
        'id': fields.IntegerField(),
        'project_id': fields.StringField(nullable=True),
        'resource': fields.StringField(),
        'hard_limit': fields.IntegerField(nullable=True),
        # NOTE(kiennt): By now, this field is only used for etcd. If using sql,
        #               this field will be None.
        'uuid': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(quota, db_quota):
        """Converts a database entity to a formal object"""
        for field in quota.fields:
            setattr(quota, field, db_quota[field])

        quota.obj_reset_changes()
        return quota

    @base.remotable_classmethod
    def get(cls, context, project_id, resource):
        """Find a quota based on project_id and resource

        :param project_id: the project id.
        :param context: security context.
        :param resource: the name of resource.
        :returns: a :class:`Quota` object.
        """
        db_quota = dbapi.quota_get(context, project_id, resource)
        quota = Quota._from_db_object(cls(context), db_quota)
        return quota

    @base.remotable_classmethod
    def get_all(cls, context, project_id):
        """Find all quotas associated with project

        :param context: security context.
        :param project_id: the project id.
        :returns: a dict
        """
        return dbapi.quota_get_all_by_project(context, project_id)

    @base.remotable
    def create(self, context):
        """Create a Quota record in the DB.

        :param context: security context. NOTE: This should only be
                        used internally by the indirection api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Quota(context)
        """
        values = self.obj_get_changes()
        project_id = values.get('project_id')
        resource = values.get('resource')
        limit = values.get('hard_limit')
        db_quota = dbapi.quota_create(context, project_id, resource, limit)
        self._from_db_object(self, db_quota)

    @base.remotable_classmethod
    def destroy_all_by_project(cls, context, project_id):
        """Destroy all quotas associated with a project.

        :param context: security context.
        :param project_id: the id of the project
        """
        dbapi.quota_destroy_all_by_project(context, project_id)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Quota from the DB.

        :param context: security context. NOTE: This should only be
                        used internally by the indirection api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Quota(context)
        """
        dbapi.quota_destroy(context, self.project_id, self.resource)
        self.obj_reset_changes()

    @base.remotable
    def update(self, context=None):
        """Save updates to this Quota.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: security context. NOTE: This should only be
                        used internally by the indirection api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Quota(context)
        """
        updates = self.obj_get_changes()
        dbapi.quota_update(context, self.project_id, self.resource,
                           updates.get('hard_limit'))
        self.obj_reset_changes()
