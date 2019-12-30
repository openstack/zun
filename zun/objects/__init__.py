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

from zun.objects import compute_node
from zun.objects import container
from zun.objects import container_action
from zun.objects import container_pci_requests
from zun.objects import exec_instance
from zun.objects import image
from zun.objects import numa
from zun.objects import pci_device
from zun.objects import pci_device_pool
from zun.objects import quota
from zun.objects import quota_class
from zun.objects import registry
from zun.objects import request_group
from zun.objects import resource_class
from zun.objects import resource_provider
from zun.objects import vif
from zun.objects import volume
from zun.objects import volume_mapping
from zun.objects import zun_network
from zun.objects import zun_service


Container = container.Container
Volume = volume.Volume
VolumeMapping = volume_mapping.VolumeMapping
ZunService = zun_service.ZunService
Image = image.Image
ZunNetwork = zun_network.ZunNetwork
NUMANode = numa.NUMANode
NUMATopology = numa.NUMATopology
ResourceProvider = resource_provider.ResourceProvider
ResourceClass = resource_class.ResourceClass
ComputeNode = compute_node.ComputeNode
Capsule = container.Capsule
CapsuleContainer = container.CapsuleContainer
CapsuleInitContainer = container.CapsuleInitContainer
PciDevice = pci_device.PciDevice
PciDevicePool = pci_device_pool.PciDevicePool
Quota = quota.Quota
QuotaClass = quota_class.QuotaClass
ContainerPCIRequest = container_pci_requests.ContainerPCIRequest
ContainerPCIRequests = container_pci_requests.ContainerPCIRequests
ContainerAction = container_action.ContainerAction
ContainerActionEvent = container_action.ContainerActionEvent
ExecInstance = exec_instance.ExecInstance
Registry = registry.Registry
RequestGroup = request_group.RequestGroup
VIFState = vif.VIFState

__all__ = (
    'Container',
    'VolumeMapping',
    'ZunService',
    'Image',
    'ZunNetwork',
    'ResourceProvider',
    'ResourceClass',
    'NUMANode',
    'NUMATopology',
    'ComputeNode',
    'Capsule',
    'CapsuleContainer',
    'CapsuleInitContainer',
    'PciDevice',
    'PciDevicePool',
    'Quota',
    'QuotaClass',
    'ContainerPCIRequest',
    'ContainerPCIRequests',
    'ContainerAction',
    'ContainerActionEvent',
    'ExecInstance',
    'Registry',
    'RequestGroup',
    'VIFState',
)
