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
class ExecInstance(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'container_id': fields.IntegerField(nullable=False),
        'exec_id': fields.StringField(nullable=False),
        'token': fields.StringField(nullable=True),
        'url': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(exec_inst, db_exec_inst):
        """Converts a database entity to a formal object."""
        for field in exec_inst.fields:
            setattr(exec_inst, field, db_exec_inst[field])

        exec_inst.obj_reset_changes()
        return exec_inst

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ExecInstance._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def list_by_container_id(cls, context, container_id):
        db_objects = dbapi.list_exec_instances(
            context, filters={'container_id': container_id})
        return ExecInstance._from_db_object_list(db_objects, cls, context)

    @base.remotable
    def create(self, context):
        values = self.obj_get_changes()
        db_exec_inst = dbapi.create_exec_instance(context, values)
        self._from_db_object(self, db_exec_inst)
