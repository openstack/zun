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

import six

from oslo_serialization import jsonutils as json
from oslo_versionedobjects import fields


class ContainerStatus(fields.Enum):
    ALL = (
        ERROR, RUNNING, STOPPED, PAUSED, UNKNOWN, CREATING,
        CREATED,
    ) = (
        'Error', 'Running', 'Stopped', 'Paused', 'Unknown', 'Creating',
        'Created',
    )

    def __init__(self):
        super(ContainerStatus, self).__init__(
            valid_values=ContainerStatus.ALL)


class ContainerStatusField(fields.BaseEnumField):
    AUTO_TYPE = ContainerStatus()


class TaskState(fields.Enum):
    ALL = (
        IMAGE_PULLING, CONTAINER_CREATING, SANDBOX_CREATING,
        CONTAINER_STARTING, CONTAINER_DELETING, SANDBOX_DELETING,
        CONTAINER_STOPPING, CONTAINER_REBOOTING,
    ) = (
        'image_pulling', 'container_creating', 'sandbox_creating',
        'container_starting', 'container_deleting', 'sandbox_deleting',
        'container_stopping', 'container_rebooting',
    )

    def __init__(self):
        super(TaskState, self).__init__(
            valid_values=TaskState.ALL)


class TaskStateField(fields.BaseEnumField):
    AUTO_TYPE = TaskState()


class ListOfIntegersField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.Integer())


class Json(fields.FieldType):
    def coerce(self, obj, attr, value):
        if isinstance(value, six.string_types):
            loaded = json.loads(value)
            return loaded
        return value

    def from_primitive(self, obj, attr, value):
        return self.coerce(obj, attr, value)

    def to_primitive(self, obj, attr, value):
        return json.dumps(value)


class JsonField(fields.AutoTypedField):
    AUTO_TYPE = Json()


class ResourceClass(fields.Enum):
    ALL = (
        VCPU, MEMORY_MB, DISK_GB, PCI_DEVICE, SRIOV_NET_VF,
        NUMA_SOCKET, NUMA_CORE, NUMA_THREAD, NUMA_MEMORY_MB,
        IPV4_ADDRESS
    ) = (
        'VCPU', 'MEMORY_MB', 'DISK_GB', 'PCI_DEVICE', 'SRIOV_NET_VF',
        'NUMA_SOCKET', 'NUMA_CORE', 'NUMA_THREAD', 'NUMA_MEMORY_MB',
        'IPV4_ADDRESS'
    )

    def __init__(self):
        super(ResourceClass, self).__init__(
            valid_values=ResourceClass.ALL)


class ResourceClassField(fields.AutoTypedField):
    AUTO_TYPE = ResourceClass()
