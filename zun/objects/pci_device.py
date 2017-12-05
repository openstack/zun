# Copyright 2017 Intel Corporation
# All Rights Reserved.
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

import copy

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from oslo_versionedobjects import fields
import six

from zun.common import exception
from zun.db import api as dbapi
from zun.objects import base
from zun.objects import fields as z_fields

LOG = logging.getLogger(__name__)


def compare_pci_device_attributes(obj_a, obj_b):
    if not isinstance(obj_b, PciDevice):
        return False
    pci_ignore_fields = base.ZunPersistentObject.fields.keys()
    for name in obj_a.obj_fields:
        if name in pci_ignore_fields:
            continue
        is_set_a = obj_a.obj_attr_is_set(name)
        is_set_b = obj_b.obj_attr_is_set(name)
        if is_set_a != is_set_b:
            return False
        if is_set_a:
            if getattr(obj_a, name) != getattr(obj_b, name):
                return False
    return True


@base.ZunObjectRegistry.register
class PciDevice(base.ZunPersistentObject, base.ZunObject):

    """Object to represent a PCI device on a compute node.

    PCI devices are managed by the compute resource tracker, which discovers
    the devices from the hardware platform, claims, allocates and frees
    devices for containers.

    The PCI device information is permanently maintained in a database.
    This makes it convenient to get PCI device information, like physical
    function for a VF device, adjacent switch IP address for a NIC,
    compute node identification for a PCI device, etc. It also provides a
    convenient way to check device allocation information for administrator
    purposes.

    A device can be in available/claimed/allocated/deleted/removed state.

    A device is available when it is discovered..

    A device is claimed prior to being allocated to an container. Normally the
    transition from claimed to allocated is quick.

    A device becomes removed when hot removed from a node (i.e. not found in
    the next auto-discover) but not yet synced with the DB. A removed device
    should not be allocated to any container.

    Filed notes::

        | 'dev_id':
        |   compute node's identification for the device.
        | 'extra_info':
        |   Device-specific properties like PF address, switch ip address etc.

    """

    # Version 1.0: Initial version
    # Version 1.1: Change compute_node_uuid to uuid type
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        # Note(yjiang5): the compute_node_uuid may be None because the pci
        # device objects are created before the compute node is created in DB
        'compute_node_uuid': fields.UUIDField(nullable=True),
        'address': fields.StringField(),
        'vendor_id': fields.StringField(),
        'product_id': fields.StringField(),
        'dev_type': z_fields.PciDeviceTypeField(),
        'status': z_fields.PciDeviceStatusField(),
        'dev_id': fields.StringField(nullable=True),
        'label': fields.StringField(nullable=True),
        'container_uuid': fields.StringField(nullable=True),
        'request_id': fields.StringField(nullable=True),
        'extra_info': fields.DictOfStringsField(),
        'numa_node': fields.IntegerField(nullable=True),
        'parent_addr': fields.StringField(nullable=True),
    }

    def update_device(self, dev_dict):
        """Sync the content from device dictionary to device object.

        The resource tracker updates the available devices periodically.
        To avoid meaningless syncs with the database, we update the device
        object only if a value changed.
        """

        # Note(yjiang5): status/container_uuid should only be updated by
        # functions like claim/allocate etc. The id is allocated by
        # database. The extra_info is created by the object.
        no_changes = ('status', 'container_uuid', 'id', 'extra_info')
        for key in no_changes:
            dev_dict.pop(key, None)

        # NOTE(ndipanov): This needs to be set as it's accessed when matching
        dev_dict.setdefault('parent_addr')

        for k, v in dev_dict.items():
            if k in self.fields.keys():
                setattr(self, k, v)
            else:
                # NOTE(yjiang5): extra_info.update does not update
                # obj_what_changed, set it explicitly
                # NOTE(ralonsoh): list of parameters currently added to
                # "extra_info" dict:
                #     - "capabilities": dict of (strings/list of strings)
                extra_info = self.extra_info
                data = (v if isinstance(v, six.string_types) else
                        jsonutils.dumps(v))
                extra_info.update({k: data})
                self.extra_info = extra_info

    def __init__(self, *args, **kwargs):
        super(PciDevice, self).__init__(*args, **kwargs)
        self.obj_reset_changes()
        self.extra_info = {}
        # NOTE(ndipanov): These are required to build an in-memory device tree
        # but don't need to be proper fields (and can't easily be as they would
        # hold circular references)
        self.parent_device = None
        self.child_devices = []

    def __eq__(self, other):
        return compare_pci_device_attributes(self, other)

    def __ne__(self, other):
        return not (self == other)

    @staticmethod
    def _from_db_object(context, pci_device, db_dev):
        for key in pci_device.fields:
            if key != 'extra_info':
                setattr(pci_device, key, db_dev[key])
            else:
                extra_info = db_dev.get("extra_info")
                pci_device.extra_info = jsonutils.loads(extra_info)
        pci_device._context = context
        pci_device.obj_reset_changes()

        return pci_device

    @base.remotable_classmethod
    def get_by_dev_addr(cls, context, compute_node_uuid, dev_addr):
        db_dev = dbapi.get_pci_device_by_addr(
            compute_node_uuid, dev_addr)
        return cls._from_db_object(context, cls(), db_dev)

    @base.remotable_classmethod
    def get_by_dev_id(cls, context, id):
        db_dev = dbapi.get_pci_device_by_id(id)
        return cls._from_db_object(context, cls(), db_dev)

    @classmethod
    def create(cls, context, dev_dict):
        """Create a PCI device based on compute node information.

        As the device object is just created and is not synced with db yet
        thus we should not reset changes here for fields from dict.
        """
        pci_device = cls(context)
        pci_device.update_device(dev_dict)
        pci_device.status = z_fields.PciDeviceStatus.AVAILABLE
        pci_device.uuid = uuidutils.generate_uuid()
        return pci_device

    @base.remotable
    def save(self):
        if self.status == z_fields.PciDeviceStatus.REMOVED:
            self.status = z_fields.PciDeviceStatus.DELETED
            dbapi.destroy_pci_device(self.compute_node_uuid,
                                     self.address)
        elif self.status != z_fields.PciDeviceStatus.DELETED:
            updates = self.obj_get_changes()
            updates['extra_info'] = self.extra_info
            updates['extra_info'] = jsonutils.dumps(updates['extra_info'])

            if updates:
                dbapi.update_pci_device(self.compute_node_uuid,
                                        self.address, updates)

    @staticmethod
    def _bulk_update_status(dev_list, status):
        for dev in dev_list:
            dev.status = status

    def claim(self, container_uuid):
        if self.status != z_fields.PciDeviceStatus.AVAILABLE:
            raise exception.PciDeviceInvalidStatus(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, status=self.status,
                hopestatus=[z_fields.PciDeviceStatus.AVAILABLE])

        if self.dev_type == z_fields.PciDeviceType.SRIOV_PF:
            # Update PF status to CLAIMED if all of it dependants are free
            # and set their status to UNCLAIMABLE
            vfs_list = self.child_devices
            if not all([vf.is_available() for vf in vfs_list]):
                raise exception.PciDeviceVFInvalidStatus(
                    compute_node_uuid=self.compute_node_uuid,
                    address=self.address)
            self._bulk_update_status(vfs_list,
                                     z_fields.PciDeviceStatus.UNCLAIMABLE)

        elif self.dev_type == z_fields.PciDeviceType.SRIOV_VF:
            # Update VF status to CLAIMED if it's parent has not been
            # previously allocated or claimed
            # When claiming/allocating a VF, it's parent PF becomes
            # unclaimable/unavailable. Therefore, it is expected to find the
            # parent PF in an unclaimable/unavailable state for any following
            # claims to a sibling VF

            parent_ok_statuses = (z_fields.PciDeviceStatus.AVAILABLE,
                                  z_fields.PciDeviceStatus.UNCLAIMABLE,
                                  z_fields.PciDeviceStatus.UNAVAILABLE)
            parent = self.parent_device
            if parent:
                if parent.status not in parent_ok_statuses:
                    raise exception.PciDevicePFInvalidStatus(
                        compute_node_uuid=self.compute_node_uuid,
                        address=self.parent_addr, status=self.status,
                        vf_address=self.address,
                        hopestatus=parent_ok_statuses)
                # Set PF status
                if parent.status == z_fields.PciDeviceStatus.AVAILABLE:
                    parent.status = z_fields.PciDeviceStatus.UNCLAIMABLE
            else:
                LOG.debug('Physical function addr: %(pf_addr)s parent of '
                          'VF addr: %(vf_addr)s was not found',
                          {'pf_addr': self.parent_addr,
                           'vf_addr': self.address})

        self.status = z_fields.PciDeviceStatus.CLAIMED
        self.container_uuid = container_uuid

    def allocate(self, container):
        ok_statuses = (z_fields.PciDeviceStatus.AVAILABLE,
                       z_fields.PciDeviceStatus.CLAIMED)
        parent_ok_statuses = (z_fields.PciDeviceStatus.AVAILABLE,
                              z_fields.PciDeviceStatus.UNCLAIMABLE,
                              z_fields.PciDeviceStatus.UNAVAILABLE)
        dependants_ok_statuses = (z_fields.PciDeviceStatus.AVAILABLE,
                                  z_fields.PciDeviceStatus.UNCLAIMABLE)
        if self.status not in ok_statuses:
            raise exception.PciDeviceInvalidStatus(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, status=self.status,
                hopestatus=ok_statuses)
        if (self.status == z_fields.PciDeviceStatus.CLAIMED and
                self.container_uuid != container.uuid):
            raise exception.PciDeviceInvalidOwner(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, owner=self.container_uuid,
                hopeowner=container.uuid)
        if self.dev_type == z_fields.PciDeviceType.SRIOV_PF:
            vfs_list = self.child_devices
            if not all([vf.status in dependants_ok_statuses for
                        vf in vfs_list]):
                raise exception.PciDeviceVFInvalidStatus(
                    compute_node_uuid=self.compute_node_uuid,
                    address=self.address)
            self._bulk_update_status(vfs_list,
                                     z_fields.PciDeviceStatus.UNAVAILABLE)

        elif (self.dev_type == z_fields.PciDeviceType.SRIOV_VF):
            parent = self.parent_device
            if parent:
                if parent.status not in parent_ok_statuses:
                    raise exception.PciDevicePFInvalidStatus(
                        compute_node_uuid=self.compute_node_uuid,
                        address=self.parent_addr, status=self.status,
                        vf_address=self.address,
                        hopestatus=parent_ok_statuses)
                # Set PF status
                parent.status = z_fields.PciDeviceStatus.UNAVAILABLE
            else:
                LOG.debug('Physical function addr: %(pf_addr)s parent of '
                          'VF addr: %(vf_addr)s was not found',
                          {'pf_addr': self.parent_addr,
                           'vf_addr': self.address})

        self.status = z_fields.PciDeviceStatus.ALLOCATED
        self.container_uuid = container.uuid

        container.pci_devices.append(copy.copy(self))

    def remove(self):
        if self.status != z_fields.PciDeviceStatus.AVAILABLE:
            raise exception.PciDeviceInvalidStatus(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, status=self.status,
                hopestatus=[z_fields.PciDeviceStatus.AVAILABLE])
        self.status = z_fields.PciDeviceStatus.REMOVED
        self.container_uuid = None
        self.request_id = None

    def free(self, container=None):
        ok_statuses = (z_fields.PciDeviceStatus.ALLOCATED,
                       z_fields.PciDeviceStatus.CLAIMED)
        free_devs = []
        if self.status not in ok_statuses:
            raise exception.PciDeviceInvalidStatus(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, status=self.status,
                hopestatus=ok_statuses)
        if container and self.container_uuid != container['uuid']:
            raise exception.PciDeviceInvalidOwner(
                compute_node_uuid=self.compute_node_uuid,
                address=self.address, owner=self.container_uuid,
                hopeowner=container['uuid'])
        if self.dev_type == z_fields.PciDeviceType.SRIOV_PF:
            # Set all PF dependants status to AVAILABLE
            vfs_list = self.child_devices
            self._bulk_update_status(vfs_list,
                                     z_fields.PciDeviceStatus.AVAILABLE)
            free_devs.extend(vfs_list)
        if self.dev_type == z_fields.PciDeviceType.SRIOV_VF:
            # Set PF status to AVAILABLE if all of it's VFs are free
            parent = self.parent_device
            if not parent:
                LOG.debug('Physical function addr: %(pf_addr)s parent of '
                          'VF addr: %(vf_addr)s was not found',
                          {'pf_addr': self.parent_addr,
                           'vf_addr': self.address})
            else:
                vfs_list = parent.child_devices
                if all([vf.is_available() for vf in vfs_list
                        if vf.id != self.id]):
                    parent.status = z_fields.PciDeviceStatus.AVAILABLE
                    free_devs.append(parent)
        old_status = self.status
        self.status = z_fields.PciDeviceStatus.AVAILABLE
        free_devs.append(self)
        self.container_uuid = None
        self.request_id = None
        if old_status == z_fields.PciDeviceStatus.ALLOCATED and container:
            existed = next((dev for dev in container.pci_devices
                            if dev.id == self.id))
            container.pci_devices.objects.remove(existed)
        return free_devs

    def is_available(self):
        return self.status == z_fields.PciDeviceStatus.AVAILABLE

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [PciDevice._from_db_object(context, cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def list_by_compute_node(cls, context, node_id):
        db_dev_list = dbapi.get_all_pci_device_by_node(node_id)
        return PciDevice._from_db_object_list(db_dev_list, cls, context)

    @base.remotable_classmethod
    def list_by_container_uuid(cls, context, uuid):
        db_dev_list = dbapi.get_all_pci_device_by_container_uuid(uuid)
        return PciDevice._from_db_object_list(db_dev_list, cls, context)

    @base.remotable_classmethod
    def list_by_parent_address(cls, context, node_id, parent_addr):
        db_dev_list = dbapi.get_all_pci_device_by_parent_addr(node_id,
                                                              parent_addr)
        return PciDevice._from_db_object_list(db_dev_list, cls, context)
