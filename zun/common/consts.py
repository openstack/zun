# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CONTAINER_STATUSES = (
    ERROR, RUNNING, STOPPED, PAUSED, UNKNOWN, CREATING, CREATED,
    DELETED, DELETING, REBUILDING, DEAD, RESTARTING
) = (
    'Error', 'Running', 'Stopped', 'Paused', 'Unknown', 'Creating', 'Created',
    'Deleted', 'Deleting', 'Rebuilding', 'Dead', 'Restarting'
)

CAPSULE_STATUSES = (
    PENDING, RUNNING, SUCCEEDED, FAILED, UNKNOWN
) = (
    'Pending', 'Running', 'Succeeded', 'Failed', 'Unknown'
)

TASK_STATES = (
    IMAGE_PULLING, CONTAINER_CREATING,
    CONTAINER_STARTING, CONTAINER_DELETING,
    CONTAINER_STOPPING, CONTAINER_REBOOTING, CONTAINER_PAUSING,
    CONTAINER_UNPAUSING, CONTAINER_KILLING, SG_ADDING,
    SG_REMOVING, NETWORK_ATTACHING, NETWORK_DETACHING,
    CONTAINER_REBUILDING,
) = (
    'image_pulling', 'container_creating',
    'container_starting', 'container_deleting',
    'container_stopping', 'container_rebooting', 'container_pausing',
    'container_unpausing', 'container_killing', 'sg_adding',
    'sg_removing', 'network_attaching', 'network_detaching',
    'container_rebuilding',
)

RESOURCE_CLASSES = (
    VCPU, MEMORY_MB, DISK_GB, PCI_DEVICE, SRIOV_NET_VF,
    NUMA_SOCKET, NUMA_CORE, NUMA_THREAD, NUMA_MEMORY_MB,
    IPV4_ADDRESS
) = (
    'VCPU', 'MEMORY_MB', 'DISK_GB', 'PCI_DEVICE', 'SRIOV_NET_VF',
    'NUMA_SOCKET', 'NUMA_CORE', 'NUMA_THREAD', 'NUMA_MEMORY_MB',
    'IPV4_ADDRESS'
)

ALLOCATED = 'allocated'

# The name of Docker container is of the form NAME_PREFIX-<uuid>
NAME_PREFIX = 'zun-'

# Storage drivers that support disk quota feature
SUPPORTED_STORAGE_DRIVERS = \
    ['devicemapper', 'overlay2', 'windowfilter', 'zfs', 'btrfs']

DEFAULT_QUOTA_CLASS_NAME = 'default'

TYPE_ANY = -1
TYPE_CONTAINER = 0
TYPE_CAPSULE = 1
TYPE_CAPSULE_CONTAINER = 2
TYPE_CAPSULE_INIT_CONTAINER = 3

CUSTOM_TRAITS = (
    ZUN_COMPUTE_STATUS_DISABLED,
) = (
    'CUSTOM_ZUN_COMPUTE_STATUS_DISABLED',
)

# neutron related constants
BINDING_PROFILE = 'binding:profile'
BINDING_HOST_ID = 'binding:host_id'
DEVICE_OWNER_ZUN = 'compute:zun'

# CNI constants
CNI_EXCEPTION_CODE = 100
CNI_TIMEOUT_CODE = 200
DEFAULT_IFNAME = 'eth0'
CNI_METADATA_VIF = 'vif'
CNI_METADATA_PID = 'pid'
USERSPACE_DRIVERS = ['vfio-pci', 'uio', 'uio_pci_generic', 'igb_uio']
