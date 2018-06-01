#    Copyright 2016 IBM, Corp.
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

"""
etcd models
"""

import etcd
from oslo_serialization import jsonutils as json

from zun.common import exception
import zun.db.etcd as db
from zun import objects


class Base(object):

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key):
        return getattr(self, key)

    def etcd_path(self, sub_path):
        return self.path + '/' + sub_path

    def as_dict(self):
        d = {}
        for f in self._fields:
            d[f] = getattr(self, f, None)

        return d

    def path_already_exist(self, client, path):
        try:
            client.read(path)
        except etcd.EtcdKeyNotFound:
            return False

        return True

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.items():
            setattr(self, k, v)

    def save(self, session=None):
        if session is None:
            session = db.api.get_backend()
        client = session.client
        path = self.etcd_path(self.uuid)

        if self.path_already_exist(client, path):
            raise exception.ResourceExists(name=getattr(self, '__class__'))

        client.write(path, json.dump_as_bytes(self.as_dict()))
        return

    def items(self):
        """Make the model object behave like a dict."""
        return self.as_dict().items()

    def iteritems(self):
        """Make the model object behave like a dict."""
        return self.as_dict().items()

    def keys(self):
        """Make the model object behave like a dict."""
        return [key for key, value in self.iteritems()]


class ZunService(Base):
    """Represents health status of various zun services"""

    _path = '/zun_services'

    _fields = objects.ZunService.fields.keys()

    def __init__(self, service_data):
        self.path = ZunService.path()
        for f in ZunService.fields():
            setattr(self, f, None)
        self.id = 1
        self.disabled = False
        self.forced_down = False
        self.report_count = 0
        self.update(service_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields

    def save(self, session=None):
        if session is None:
            session = db.api.get_backend()
        client = session.client
        path = self.etcd_path(self.host + '_' + self.binary)

        if self.path_already_exist(client, path):
            raise exception.ZunServiceAlreadyExists(host=self.host,
                                                    binary=self.binary)

        client.write(path, json.dump_as_bytes(self.as_dict()))
        return


class Container(Base):
    """Represents a container."""

    _path = '/containers'

    _fields = objects.Container.fields.keys()

    def __init__(self, container_data):
        self.path = Container.path()
        for f in Container.fields():
            setattr(self, f, None)
        self.id = 1
        self.disk = 0
        self.auto_remove = False
        self.interactive = False
        self.auto_heal = False
        self.update(container_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class Image(Base):
    """Represents a container image."""

    _path = '/images'

    _fields = objects.Image.fields.keys()

    def __init__(self, image_data):
        self.path = Image.path()
        for f in Image.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(image_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class ResourceClass(Base):
    """Represents a resource class."""

    _path = '/resource_classes'

    _fields = objects.ResourceClass.fields.keys()

    def __init__(self, resource_class_data):
        self.path = ResourceClass.path()
        for f in ResourceClass.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(resource_class_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class Capsule(Base):
    """Represents a capsule."""

    _path = '/capsules'

    _fields = objects.Capsule.fields.keys()

    def __init__(self, capsule_data):
        self.path = Capsule.path()
        for f in Capsule.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(capsule_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class ComputeNode(Base):
    """Represents a compute node. """
    _path = '/compute_nodes'

    # NOTE(kiennt): Use list(fields) instead of fields.keys()
    #               because in Python 3, the dict.keys() method
    #               returns a dictionary view object, which acts
    #               as a set. To do the replacement, _fields should
    #               be a list.
    _fields = list(objects.ComputeNode.fields)

    def __init__(self, compute_node_data):
        self.path = ComputeNode.path()
        for f in ComputeNode.fields():
            setattr(self, f, None)
        self.cpus = 0
        self.cpu_used = 0
        self.mem_used = 0
        self.mem_total = 0
        self.mem_free = 0
        self.mem_available = 0
        self.total_containers = 0
        self.stopped_containers = 0
        self.paused_containers = 0
        self.running_containers = 0
        self.disk_used = 0
        self.disk_total = 0
        self.disk_quota_supported = False
        self.update(compute_node_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        # NOTE(kiennt): The pci_device_pools field in object maps to the
        #               pci_stats field in the database. Therefore, need
        #               replace these fields.
        for index, value in enumerate(cls._fields):
            if value == 'pci_device_pools':
                cls._fields.pop(index)
                cls._fields.insert(index, 'pci_stats')
                break
        return cls._fields

    def save(self, session=None):
        if session is None:
            session = db.api.get_backend()
        client = session.client
        path = self.etcd_path(self.uuid)
        if self.path_already_exist(client, path):
            raise exception.ComputeNodeAlreadyExists(
                field='UUID', value=self.uuid)

        client.write(path, json.dump_as_bytes(self.as_dict()))
        return


class PciDevice(Base):
    """Represents a PciDevice. """
    _path = '/pcidevices'

    _fields = objects.PciDevice.fields.keys()

    def __init__(self, pci_data):
        self.path = PciDevice.path()
        for f in PciDevice.fields():
            setattr(self, f, None)
        self.id = 1
        self.numa_node = 0
        self.update(pci_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class VolumeMapping(Base):
    """Represents a VolumeMapping."""
    _path = '/volume_mapping'

    _fields = objects.VolumeMapping.fields.keys()

    def __init__(self, volume_mapping_data):
        self.path = VolumeMapping.path()
        for f in VolumeMapping.fields():
            setattr(self, f, None)
        self.id = 1
        self.auto_remove = False
        self.update(volume_mapping_data)

    @classmethod
    def path(cls):
        return cls._path

    @classmethod
    def fields(cls):
        return cls._fields


class ContainerAction(Base):
    """Represents a container action.

    The intention is that there will only be one of these pre user request. A
    lookup by(container_uuid, request_id) should always return a single result.
    """
    _path = '/container_actions'

    _fields = list(objects.ContainerAction.fields) + ['uuid']

    def __init__(self, action_data):
        self.path = ContainerAction.path(action_data['container_uuid'])
        for f in ContainerAction.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(action_data)

    @classmethod
    def path(cls, container_uuid):
        return cls._path + '/' + container_uuid

    @classmethod
    def fields(cls):
        return cls._fields


class ContainerActionEvent(Base):
    """Track events that occur during an ContainerAction."""

    _path = '/container_actions_events'

    _fields = list(objects.ContainerActionEvent.fields) + ['action_uuid',
                                                           'uuid']

    def __init__(self, event_data):
        self.path = ContainerActionEvent.path(event_data['action_uuid'])
        for f in ContainerActionEvent.fields():
            setattr(self, f, None)
        self.id = 1
        self.action_id = 0
        self.update(event_data)

    @classmethod
    def path(cls, action_uuid):
        return cls._path + '/' + action_uuid

    @classmethod
    def fields(cls):
        return cls._fields


class Quota(Base):

    """Represents a Quota."""
    _path = '/quotas'

    _fields = list(objects.Quota.fields) + ['uuid']

    def __init__(self, quota_data):
        self.path = Quota.path(project_id=quota_data.get('class_name'),
                               resource=quota_data.get('resource'))
        for f in Quota.fields():
            setattr(self, f, None)
        self.id = 1
        self.update(quota_data)

    @classmethod
    def path(cls, project_id, resource=None):
        if resource is not None:
            path = '{}/{}/{}' . format(cls._path, project_id, resource)
        else:
            path = '{}/{}' . format(cls._path, project_id)
        return path

    @classmethod
    def fields(cls):
        return cls._fields


class QuotaClass(Base):

    """Represents a QuotaClass."""
    _path = '/quota_classes'

    _fields = list(objects.QuotaClass.fields) + ['uuid']

    def __init__(self, quota_class_data):
        self.path = QuotaClass.path(
            class_name=quota_class_data.get('class_name'),
            resource=quota_class_data.get('resource'))

        for f in QuotaClass.fields():
            setattr(self, f, None)

        self.id = 1
        self.update(quota_class_data)

    @classmethod
    def path(cls, class_name, resource=None):
        if resource is not None:
            path = '{}/{}/{}' . format(cls._path, class_name, resource)
        else:
            path = '{}/{}' . format(cls._path, class_name)
        return path

    @classmethod
    def fields(cls):
        return cls._fields


class QuotaUsage(Base):

    """Represents the current usage for a given resource."""

    _path = '/quota_usages'

    _fields = ['id', 'project_id', 'resource', 'in_use', 'reserved']

    def __init__(self, quota_usage_data):
        self.path = QuotaUsage.path(
            project_id=quota_usage_data['project_id'],
            resource=quota_usage_data['resource'])

        for f in QuotaUsage.fields():
            setattr(self, f, None)

        self.id = 1
        self.update(quota_usage_data)

    @classmethod
    def path(cls, project_id, resource):
        return '{}/{}/{}' . format(cls._path, project_id, resource)

    @classmethod
    def fields(cls):
        return cls._fields
