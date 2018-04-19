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
    IMAGE_PULLING, CONTAINER_CREATING, SANDBOX_CREATING,
    CONTAINER_STARTING, CONTAINER_DELETING, SANDBOX_DELETING,
    CONTAINER_STOPPING, CONTAINER_REBOOTING, CONTAINER_PAUSING,
    CONTAINER_UNPAUSING, CONTAINER_KILLING, SG_ADDING,
    SG_REMOVING, NETWORK_ATTACHING, NETWORK_DETACHING
) = (
    'image_pulling', 'container_creating', 'sandbox_creating',
    'container_starting', 'container_deleting', 'sandbox_deleting',
    'container_stopping', 'container_rebooting', 'container_pausing',
    'container_unpausing', 'container_killing', 'sg_adding',
    'sg_removing', 'network_attaching', 'network_detaching'
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
SANDBOX_NAME_PREFIX = 'zun-sandbox-'

# Storage drivers that support disk quota feature
SUPPORTED_STORAGE_DRIVERS = \
    ['devicemapper', 'overlay2', 'windowfilter', 'zfs', 'btrfs']

DEFAULT_QUOTA_CLASS_NAME = 'default'
