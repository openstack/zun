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

from zun.common import consts

UnspecifiedDefault = fields.UnspecifiedDefault


class BaseZunEnum(fields.Enum):
    def __init__(self, **kwargs):
        super(BaseZunEnum, self).__init__(valid_values=self.__class__.ALL)


class ContainerStatus(fields.Enum):
    ALL = consts.CONTAINER_STATUSES

    def __init__(self):
        super(ContainerStatus, self).__init__(
            valid_values=ContainerStatus.ALL)


class ContainerStatusField(fields.BaseEnumField):
    AUTO_TYPE = ContainerStatus()


class CapsuleStatus(fields.Enum):
    ALL = consts.CAPSULE_STATUSES

    def __init__(self):
        super(CapsuleStatus, self).__init__(
            valid_values=CapsuleStatus.ALL)


class CapsuleStatusField(fields.BaseEnumField):
    AUTO_TYPE = CapsuleStatus()


class TaskState(fields.Enum):
    ALL = consts.TASK_STATES

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
        return json.dump_as_bytes(value)


class JsonField(fields.AutoTypedField):
    AUTO_TYPE = Json()


class ResourceClass(fields.Enum):
    ALL = consts.RESOURCE_CLASSES

    def __init__(self):
        super(ResourceClass, self).__init__(
            valid_values=ResourceClass.ALL)


class ResourceClassField(fields.AutoTypedField):
    AUTO_TYPE = ResourceClass()


class PciDeviceStatus(BaseZunEnum):

    AVAILABLE = "available"
    CLAIMED = "claimed"
    ALLOCATED = "allocated"
    REMOVED = "removed"  # The device has been hot-removed and not yet deleted
    DELETED = "deleted"  # The device is marked not available/deleted.
    UNCLAIMABLE = "unclaimable"
    UNAVAILABLE = "unavailable"

    ALL = (AVAILABLE, CLAIMED, ALLOCATED, REMOVED, DELETED, UNAVAILABLE,
           UNCLAIMABLE)


class PciDeviceType(BaseZunEnum):

    STANDARD = "PCI"
    SRIOV_PF = "PF"
    SRIOV_VF = "VF"

    ALL = (STANDARD, SRIOV_PF, SRIOV_VF)


class PciDeviceTypeField(fields.BaseEnumField):
        AUTO_TYPE = PciDeviceType()


class PciDeviceStatusField(fields.BaseEnumField):
        AUTO_TYPE = PciDeviceStatus()
