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
from zun.objects import exec_instance as exec_inst
from zun.objects import fields as z_fields
from zun.objects import pci_device


LOG = logging.getLogger(__name__)


CONTAINER_OPTIONAL_ATTRS = ["pci_devices", "exec_instances"]


@base.ZunObjectRegistry.register
class Container(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    # Version 1.1: Add container_id column
    # Version 1.2: Add memory column
    # Version 1.3: Add task_state column
    # Version 1.4: Add cpu, workdir, ports, hostname and labels columns
    # Version 1.5: Add meta column
    # Version 1.6: Add addresses column
    # Version 1.7: Add host column
    # Version 1.8: Add restart_policy
    # Version 1.9: Add status_detail column
    # Version 1.10: Add tty, stdin_open
    # Version 1.11: Add image_driver
    # Version 1.12: Add 'Created' to ContainerStatus
    # Version 1.13: Add more task states for container
    # Version 1.14: Add method 'list_by_host'
    # Version 1.15: Combine tty and stdin_open
    # Version 1.16: Add websocket_url and token
    # Version 1.17: Add security_groups
    # Version 1.18: Add auto_remove
    # Version 1.19: Add runtime column
    # Version 1.20: Change runtime to String type
    # Version 1.21: Add pci_device attribute
    # Version 1.22: Add 'Deleting' to ContainerStatus
    # Version 1.23: Add the missing 'pci_devices' attribute
    # Version 1.24: Add the storage_opt attribute
    # Version 1.25: Change TaskStateField definition
    # Version 1.26:  Add auto_heal
    # Version 1.27: Make auto_heal field nullable
    # Version 1.28: Add 'Dead' to ContainerStatus
    # Version 1.29: Add 'Restarting' to ContainerStatus
    # Version 1.30: Add capsule_id attribute
    # Version 1.31: Add 'started_at' attribute
    # Version 1.32: Add 'exec_instances' attribute
    VERSION = '1.33'

    fields = {
        'id': fields.IntegerField(),
        'container_id': fields.StringField(nullable=True),
        'uuid': fields.UUIDField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'image': fields.StringField(nullable=True),
        'cpu': fields.FloatField(nullable=True),
        'memory': fields.StringField(nullable=True),
        'command': fields.ListOfStringsField(nullable=True),
        'status': z_fields.ContainerStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),
        'task_state': z_fields.TaskStateField(nullable=True),
        'environment': fields.DictOfStringsField(nullable=True),
        'workdir': fields.StringField(nullable=True),
        'auto_remove': fields.BooleanField(nullable=True),
        'ports': z_fields.ListOfIntegersField(nullable=True),
        'hostname': fields.StringField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'meta': fields.DictOfStringsField(nullable=True),
        'addresses': z_fields.JsonField(nullable=True),
        'image_pull_policy': fields.StringField(nullable=True),
        'host': fields.StringField(nullable=True),
        'restart_policy': fields.DictOfStringsField(nullable=True),
        'status_detail': fields.StringField(nullable=True),
        'interactive': fields.BooleanField(nullable=True),
        'image_driver': fields.StringField(nullable=True),
        'websocket_url': fields.StringField(nullable=True),
        'websocket_token': fields.StringField(nullable=True),
        'security_groups': fields.ListOfStringsField(nullable=True),
        'runtime': fields.StringField(nullable=True),
        'pci_devices': fields.ListOfObjectsField('PciDevice',
                                                 nullable=True),
        'disk': fields.IntegerField(nullable=True),
        'auto_heal': fields.BooleanField(nullable=True),
        'capsule_id': fields.IntegerField(nullable=True),
        'started_at': fields.DateTimeField(tzinfo_aware=False, nullable=True),
        'exec_instances': fields.ListOfObjectsField('ExecInstance',
                                                    nullable=True),
    }

    @staticmethod
    def _from_db_object(container, db_container):
        """Converts a database entity to a formal object."""
        for field in container.fields:
            if field in ['pci_devices', 'exec_instances']:
                continue
            setattr(container, field, db_container[field])

        container.obj_reset_changes()
        return container

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Container._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a container based on uuid and return a :class:`Container` object.

        :param uuid: the uuid of a container.
        :param context: Security context
        :returns: a :class:`Container` object.
        """
        db_container = dbapi.get_container_by_uuid(context, uuid)
        container = Container._from_db_object(cls(context), db_container)
        return container

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a container based on name and return a Container object.

        :param name: the logical name of a container.
        :param context: Security context
        :returns: a :class:`Container` object.
        """
        db_container = dbapi.get_container_by_name(context, name)
        container = Container._from_db_object(cls(context), db_container)
        return container

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Container objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filters when list containers, the filter name could be
                        'name', 'image', 'project_id', 'user_id', 'memory'.
                        For example, filters={'image': 'nginx'}
        :returns: a list of :class:`Container` object.

        """
        db_containers = dbapi.list_containers(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return Container._from_db_object_list(db_containers, cls, context)

    @base.remotable_classmethod
    def list_by_host(cls, context, host):
        """Return a list of Container objects by host.

        :param context: Security context.
        :param host: A compute host.
        :returns: a list of :class:`Container` object.

        """
        db_containers = dbapi.list_containers(context, filters={'host': host})
        return Container._from_db_object_list(db_containers, cls, context)

    @base.remotable_classmethod
    def list_by_capsule_id(cls, context, capsule_id):
        """Return a list of Container objects by capsule_id.

        :param context: Security context.
        :param host: A capsule id.
        :returns: a list of :class:`Container` object.

        """
        db_containers = dbapi.list_containers(
            context, filters={'capsule_id': capsule_id})
        return Container._from_db_object_list(db_containers, cls, context)

    @base.remotable
    def create(self, context):
        """Create a Container record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)

        """
        values = self.obj_get_changes()
        db_container = dbapi.create_container(context, values)
        self._from_db_object(self, db_container)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Container from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        dbapi.destroy_container(context, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Container.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        updates = self.obj_get_changes()
        dbapi.update_container(context, self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Container.

        Loads a container with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded container column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))

    def get_sandbox_id(self):
        if self.meta:
            return self.meta.get('sandbox_id', None)
        else:
            return None

    def set_sandbox_id(self, sandbox_id):
        if self.meta is None:
            self.meta = {'sandbox_id': sandbox_id}
        else:
            self.meta['sandbox_id'] = sandbox_id
            self._changed_fields.add('meta')

    def obj_load_attr(self, attrname):
        if attrname not in CONTAINER_OPTIONAL_ATTRS:
            raise exception.ObjectActionError(
                action='obj_load_attr',
                reason=_('attribute %s not lazy-loadable') % attrname)

        if not self._context:
            raise exception.OrphanedObjectError(method='obj_load_attr',
                                                objtype=self.obj_name())

        LOG.debug("Lazy-loading '%(attr)s' on %(name)s uuid %(uuid)s",
                  {'attr': attrname,
                   'name': self.obj_name(),
                   'uuid': self.uuid,
                   })

        # NOTE(danms): We handle some fields differently here so that we
        # can be more efficient
        if attrname == 'pci_devices':
            self._load_pci_devices()

        if attrname == 'exec_instances':
            self._load_exec_instances()

        self.obj_reset_changes([attrname])

    def _load_pci_devices(self):
        self.pci_devices = pci_device.PciDevice.list_by_container_uuid(
            self._context, self.uuid)

    def _load_exec_instances(self):
        self.exec_instances = exec_inst.ExecInstance.list_by_container_id(
            self._context, self.id)
