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
from zun.objects.numa import NUMATopology


@base.ZunObjectRegistry.register
class ComputeNode(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'uuid': fields.UUIDField(read_only=True, nullable=False),
        'numa_topology': fields.ObjectField('NUMATopology', nullable=True),
        'hostname': fields.StringField(nullable=False),
    }

    @staticmethod
    def _from_db_object(context, compute_node, db_compute_node):
        """Converts a database entity to a formal object."""
        for field in compute_node.fields:
            if field == 'numa_topology':
                numa_obj = NUMATopology._from_dict(
                    db_compute_node['numa_topology'])
                compute_node.numa_topology = numa_obj
            else:
                setattr(compute_node, field, db_compute_node[field])

        compute_node.obj_reset_changes(recursive=True)
        return compute_node

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ComputeNode._from_db_object(context, cls(context), obj)
                for obj in db_objects]

    @base.remotable
    def create(self, context):
        """Create a compute node record in the DB.

        :param context: Security context.

        """
        values = self.obj_get_changes()
        numa_obj = values.pop('numa_topology', None)
        if numa_obj is not None:
            values['numa_topology'] = numa_obj._to_dict()

        db_compute_node = dbapi.create_compute_node(context, values)
        self._from_db_object(context, self, db_compute_node)

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a compute node based on uuid.

        :param uuid: the uuid of a compute node.
        :param context: Security context
        :returns: a :class:`ComputeNode` object.
        """
        db_compute_node = dbapi.get_compute_node(context, uuid)
        compute_node = ComputeNode._from_db_object(
            context, cls(context), db_compute_node)
        return compute_node

    @base.remotable_classmethod
    def get_by_hostname(cls, context, hostname):
        db_compute_node = dbapi.get_compute_node_by_hostname(
            context, hostname)
        return cls._from_db_object(context, cls(), db_compute_node)

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of ComputeNode objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list resource providers.
        :returns: a list of :class:`ComputeNode` object.

        """
        db_compute_nodes = dbapi.list_compute_nodes(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return ComputeNode._from_db_object_list(
            db_compute_nodes, cls, context)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ComputeNode from the DB.

        :param context: Security context.
        """
        dbapi.destroy_compute_node(context, self.uuid)
        self.obj_reset_changes(recursive=True)

    @base.remotable
    def save(self, context=None):
        """Save updates to this ComputeNode.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context.
        """
        updates = self.obj_get_changes()
        dbapi.update_compute_node(context, self.uuid, updates)
        self.obj_reset_changes(recursive=True)

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this ComputeNode.

        Loads a compute node with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded compute node column by column, if there are any
        updates.

        :param context: Security context.
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
