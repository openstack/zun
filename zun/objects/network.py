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
class Network(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'name': fields.StringField(nullable=True),
        'network_id': fields.StringField(nullable=True),
        'neutron_net_id': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(network, db_network):
        """Converts a database entity to a formal object."""
        for field in network.fields:
            setattr(network, field, db_network[field])

        network.obj_reset_changes()
        return network

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Network._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find an network based on uuid and return a :class:`Network` object.

        :param uuid: the uuid of a network.
        :param context: Security context
        :returns: a :class:`Network` object.
        """
        db_network = dbapi.get_network_by_uuid(context, uuid)
        network = Network._from_db_object(cls(context), db_network)
        return network

    @base.remotable
    def create(self, context):
        """Create a Network record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Network(context)

        """
        values = self.obj_get_changes()
        db_network = dbapi.create_network(context, values)
        self._from_db_object(self, db_network)

    @base.remotable
    def save(self, context=None):
        """Save updates to this Network.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Network(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_network(context, self.uuid, updates)

        self.obj_reset_changes()
