# Copyright 2017 OpenStack Foundation
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

# Define supported virtual NIC types. VNIC_TYPE_DIRECT and VNIC_TYPE_MACVTAP
# are used for SR-IOV ports
VNIC_TYPE_NORMAL = 'normal'
VNIC_TYPE_DIRECT = 'direct'
VNIC_TYPE_MACVTAP = 'macvtap'
VNIC_TYPE_DIRECT_PHYSICAL = 'direct-physical'
VNIC_TYPE_BAREMETAL = 'baremetal'
VNIC_TYPE_VIRTIO_FORWARDER = 'virtio-forwarder'

# Define list of ports which needs pci request.
# Note: The macvtap port needs a PCI request as it is a tap interface
# with VF as the lower physical interface.
# Note: Currently, VNIC_TYPE_VIRTIO_FORWARDER assumes a 1:1
# relationship with a VF. This is expected to change in the future.
VNIC_TYPES_SRIOV = (VNIC_TYPE_DIRECT, VNIC_TYPE_MACVTAP,
                    VNIC_TYPE_DIRECT_PHYSICAL, VNIC_TYPE_VIRTIO_FORWARDER)

# Define list of ports which are passthrough to the guest
# and need a special treatment on snapshot and suspend/resume
VNIC_TYPES_DIRECT_PASSTHROUGH = (VNIC_TYPE_DIRECT,
                                 VNIC_TYPE_DIRECT_PHYSICAL)
