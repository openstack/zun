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
class QuotaClass(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add uuid column
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'class_name': fields.StringField(nullable=True),
        'resource': fields.StringField(nullable=True),
        'hard_limit': fields.IntegerField(nullable=True),
        # NOTE(kiennt): By now, this field is only used for etcd. If using sql,
        #               this field will be None.
        'uuid': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_method(quota_class, db_quota_class):
        """Convert a database entity to a format object"""
        for field in quota_class.fields:
            setattr(quota_class, field, db_quota_class[field])

        quota_class.obj_reset_changes()
        return quota_class

    @base.remotable_classmethod
    def get(cls, context, class_name, resource):
        """Find a quota class based on class_name and resource name.

        :param class_name: the name of class.
        :param context: security context.
        :param resource: the name of resource.
        :returns: a :class:`QuotaClass` object.
        """
        db_quota_class = dbapi.quota_class_get(context, class_name, resource)
        quota_class = QuotaClass._from_db_method(cls(context), db_quota_class)
        return quota_class

    @base.remotable_classmethod
    def get_all(cls, context, class_name=None):
        """Find quota based on class_name

        :param context: security context.
        :param class_name: the class name.
        :returns: a dict
        """
        if class_name is None:
            res = dbapi.quota_class_get_default(context)
        else:
            res = dbapi.quota_class_get_all_by_name(context, class_name)
        return res

    @base.remotable
    def create(self, context):
        """Create a QuotaClass record in the DB.

        :param context: security context. NOTE: This should only be
                        used internally by the indirection api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: QuotaClass(context)
        """
        values = self.obj_get_changes()
        class_name = values.get('class_name')
        resource = values.get('resource')
        limit = values.get('hard_limit')
        dbapi.quota_class_create(context, class_name, resource, limit)

    @base.remotable
    def update(self, context=None):
        """Save updates to this QuotaClass.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: security context. NOTE: This should only be
                        used internally by the indirection api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: QuotaClass(context)
        """
        updates = self.obj_get_changes()
        limit = updates.get('hard_limit')
        dbapi.quota_class_update(context, self.class_name,
                                 self.resource, limit)
