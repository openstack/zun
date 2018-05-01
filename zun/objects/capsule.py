#    Copyright 2017 ARM Holdings.
#
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

from zun.common import exception
from zun.db import api as dbapi
from zun.objects import base
from zun.objects import container
from zun.objects import fields as z_fields


LOG = logging.getLogger(__name__)


_CAPSULE_OPTIONAL_JOINED_FIELD = ['containers']
CAPSULE_OPTIONAL_ATTRS = _CAPSULE_OPTIONAL_JOINED_FIELD


@base.ZunObjectRegistry.register
class Capsule(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add host to capsule
    # Version 1.2: Change the properties of meta_labels
    # Version 1.3: Add 'Deleting' to ContainerStatus
    # Version 1.4: Add addresses and volumes_info
    # Version 1.5: Change the properties of restort_policy
    # Version 1.6: Change the type of status
    VERSION = '1.6'

    fields = {
        'capsule_version': fields.StringField(nullable=True),
        'kind': fields.StringField(nullable=True),
        'restart_policy': fields.StringField(nullable=True),
        'host_selector': fields.StringField(nullable=True),
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),

        'status': z_fields.CapsuleStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),
        'cpu': fields.FloatField(nullable=True),
        'memory': fields.StringField(nullable=True),
        'addresses': z_fields.JsonField(nullable=True),

        # conclude the readable message
        # 'key': 'value'--> 'time':'message'
        # wait until zun notify is finished
        # 'message': fields.DictOfStringsField(nullable=True),

        'spec': z_fields.JsonField(nullable=True),
        'meta_name': fields.StringField(nullable=True),
        'meta_labels': fields.DictOfStringsField(nullable=True),
        'containers': fields.ListOfObjectsField('Container', nullable=True),
        # The list of containers uuids inside the capsule
        'containers_uuids': fields.ListOfStringsField(nullable=True),
        'host': fields.StringField(nullable=True),

        # volumes_info records the volume and container attached
        # relationship:
        # {'<volume-uuid1>': ['<container-uuid1>', '<container-uuid2>'],
        # '<volume-uuid2>': ['<container-uuid2>', '<container-uuid3>']},
        # one container can attach at least one volume, also will support
        # one volume multiple in the future.
        'volumes_info': z_fields.JsonField(nullable=True),
    }

    @staticmethod
    def _from_db_object(capsule, db_capsule):
        """Converts a database entity to a formal object."""
        for field in capsule.fields:
            if field in CAPSULE_OPTIONAL_ATTRS:
                continue
            setattr(capsule, field, db_capsule[field])
        capsule.obj_reset_changes()
        return capsule

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Capsule._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a capsule based on uuid and return a :class:`Capsule` object.

        :param uuid: the uuid of a capsule.
        :param context: Security context
        :returns: a :class:`Capsule` object.
        """
        db_capsule = dbapi.get_capsule_by_uuid(context, uuid)
        capsule = Capsule._from_db_object(cls(context), db_capsule)
        return capsule

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a capsule based on name and return a :class:`Capsule` object.

        :param name: the meta_name of a capsule.
        :param context: Security context
        :returns: a :class:`Capsule` object.
        """
        db_capsule = dbapi.get_capsule_by_meta_name(context, name)
        capsule = Capsule._from_db_object(cls(context), db_capsule)
        return capsule

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Capsule objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list capsules, the filter name could be
                        'name', 'image', 'project_id', 'user_id', 'memory'.
                        For example, filters={'image': 'nginx'}
        :returns: a list of :class:`Capsule` object.

        """
        db_capsules = dbapi.list_capsules(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return Capsule._from_db_object_list(db_capsules, cls, context)

    @base.remotable
    def create(self, context):
        """Create a Container record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Capsule(context)

        """
        values = self.obj_get_changes()
        if 'containers' in values:
            raise exception.ObjectActionError(action='create',
                                              reason='containers assigned')

        db_capsule = dbapi.create_capsule(context, values)
        self._from_db_object(self, db_capsule)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Container from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Capsule(context)
        """
        dbapi.destroy_capsule(context, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Capsule.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Capsule(context)
        """
        updates = self.obj_get_changes()
        if 'containers' in updates:
            raise exception.ObjectActionError(action='save',
                                              reason='containers changed')
        dbapi.update_capsule(context, self.uuid, updates)

        self.obj_reset_changes()

    def as_dict(self):
        capsule_dict = super(Capsule, self).as_dict()
        capsule_dict['containers'] = [c.as_dict() for c in self.containers]
        return capsule_dict

    def obj_load_attr(self, attrname):
        if attrname not in CAPSULE_OPTIONAL_ATTRS:
            raise exception.ObjectActionError(
                action='obj_load_attr',
                reason='attribute %s not lazy-loadable' % attrname)
        if not self._context:
            raise exception.OrphanedObjectError(method='obj_load_attr',
                                                objtype=self.obj_name())

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s uuid %(uuid)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   'uuid': self.uuid,
                   })

        if attrname == 'containers':
            self.containers = container.Container.list_by_capsule_id(
                self._context, self.id)

        self.obj_reset_changes(fields=[attrname])
