# Copyright 2017 IBM Corp
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

from oslo_concurrency import processutils
from oslo_serialization import jsonutils

from zun.common import exception
from zun.common import utils
from zun import objects
from zun.objects import fields
from zun.pci import utils as pci_utils


class Host(object):

    def __init__(self):
        self.capabilities = None

    def get_cpu_numa_info(self):
        """This method returns a dict containing the cpuset info for a host"""

        raise NotImplementedError()

    def get_host_numa_topology(self, numa_topo_obj):
        # Replace this call with a more generic call when we obtain other
        # NUMA related data like memory etc.
        cpu_info = self.get_cpu_numa_info()
        floating_cpus = utils.get_floating_cpu_set()
        numa_node_obj = []
        for node, cpuset in cpu_info.items():
            numa_node = objects.NUMANode()
            if floating_cpus:
                allowed_cpus = set(cpuset) - (floating_cpus & set(cpuset))
            else:
                allowed_cpus = set(cpuset)
            numa_node.id = node
            # allowed_cpus are the ones allowed to pin on.
            # Rest of the cpus are assumed to be floating
            # in nature.
            numa_node.cpuset = allowed_cpus
            numa_node.pinned_cpus = set([])
            numa_node_obj.append(numa_node)
        numa_topo_obj.nodes = numa_node_obj

    def get_host_mem(self):
        with open('/proc/meminfo') as fp:
            m = fp.read().split()
            idx1 = m.index('MemTotal:')
            mem_total = m[idx1 + 1]
            idx2 = m.index('MemFree:')
            mem_free = m[idx2 + 1]
            # MemAvailable is not available until 3.14 kernel
            if 'MemAvailable:' in m:
                idx3 = m.index('MemAvailable:')
                mem_ava = m[idx3 + 1]
            else:
                idx31 = m.index('Buffers:')
                buffers = m[idx31 + 1]
                idx32 = m.index('Cached:')
                cached = m[idx32 + 1]
                mem_ava = int(mem_free) + int(buffers) + int(cached)
            mem_used = int(mem_total) - int(mem_ava)
        return int(mem_total), int(mem_free), int(mem_ava), int(mem_used)

    def get_pci_resources(self):
        addresses = []
        try:
            output, status = utils.execute('lspci', '-D', '-nnmm')
            lines = output.split('\n')
            for line in lines:
                if not line:
                    continue
                columns = line.split()
                address = columns[0]
                addresses.append(address)
        except processutils.ProcessExecutionError:
            raise exception.CommandError(cmd='lspci')

        pci_info = []
        for addr in addresses:
            pci_info.append(self._get_pci_dev_info(addr))

        return jsonutils.dumps(pci_info)

    def _get_pci_dev_info(self, address):
        """Returns a dict of PCI device."""

        def _get_device_type(address):
            """Get a PCI device's device type.

            An assignable PCI device can be a normal PCI device,
            a SR-IOV Physical Function (PF), or a SR-IOV Virtual
            Function (VF). Only normal PCI devices or SR-IOV VFs
            are assignable.
            """
            path = '/sys/bus/pci/devices/' + address + '/'
            output, status = utils.execute('ls', path)
            if "physfn" in output:
                phys_address = None
                upath = '/sys/bus/pci/devices/%s/physfn/uevent' % address
                ou, st = utils.execute('cat', upath)
                lines = ou.split('\n')
                for line in lines:
                    if 'PCI_SLOT_NAME' in line:
                        columns = line.split("=")
                        phys_address = columns[1]
                return {'dev_type': fields.PciDeviceType.SRIOV_VF,
                        'parent_addr': phys_address}
            if "virtfn" in output:
                return {'dev_type': fields.PciDeviceType.SRIOV_PF}
            return {'dev_type': fields.PciDeviceType.STANDARD}

        def _get_device_capabilities(device, address):
            """Get PCI VF device's additional capabilities.

            If a PCI device is a virtual function, this function reads the PCI
            parent's network capabilities (must be always a NIC device) and
            appends this information to the device's dictionary.
            """
            if device.get('dev_type') == fields.PciDeviceType.SRIOV_VF:
                pcinet_info = self._get_pcinet_info(address)
                if pcinet_info:
                    return {'capabilities':
                            {'network': pcinet_info.get('capabilities')}}
            return {}

        def _get_vendor_and_product(address):
            output, status = utils.execute('lspci', '-n', '-s', address)
            value = output.split()[2]
            result = value.split(":")
            return result[0], result[1]

        def _get_numa_node(address):
            numa_node = None
            output, status = utils.execute('lspci', '-vmm', '-s', address)
            lines = output.split('\n')
            for line in lines:
                if 'NUMANode' in line:
                    numa_node = int(line.split(":")[1])
            return numa_node

        dev_name = 'pci_' + address.replace(":", "_").replace(".", "_")
        vendor_id, product_id = _get_vendor_and_product(address)
        numa_node = _get_numa_node(address)
        device = {
            "dev_id": dev_name,
            "address": address,
            "product_id": product_id,
            "vendor_id": vendor_id,
            "numa_node": numa_node
        }
        device['label'] = 'label_%(vendor_id)s_%(product_id)s' % device
        device.update(_get_device_type(address))
        device.update(_get_device_capabilities(device, address))
        return device

    def _get_pcinet_info(self, vf_address):
        """Returns a dict of NET device."""
        devname = pci_utils.get_net_name_by_vf_pci_address(vf_address)
        if not devname:
            return

        ifname = pci_utils.get_ifname_by_pci_address(vf_address)
        # Features from the that libvirt supported, get them by ethtool -k
        # Note: I cannot find the rdma feature returned by ethtool, correct me
        # if the string is wrong.
        FEATURES_LIST = ['rx-checksumming', 'tx-checksumming',
                         'scatter-gather', 'tcp-segmentation-offload',
                         'generic-segmentation-offload',
                         'generic-receive-offload', 'large-receive-offload',
                         'rx-vlan-offload', 'tx-vlan-offload',
                         'ntuple-filters', 'receive-hashing',
                         'tx-udp_tnl-segmentation', 'rdma']
        FEATURES_MAP = {'rx-checksumming': 'rx',
                        'tx-checksumming': 'tx',
                        'scatter-gather': 'sg',
                        'tcp-segmentation-offload': 'tso',
                        'generic-segmentation-offload': 'gso',
                        'generic-receive-offload': 'gro',
                        'large-receive-offload': 'lro',
                        'rx-vlan-offload': 'rxvlan',
                        'tx-vlan-offload': 'txvlan',
                        'ntuple-filters': 'ntuple',
                        'receive-hashing': 'rxhash',
                        'tx-udp_tnl-segmentation': 'txudptnl',
                        'rdma': 'rdma'}

        features = []
        output, status = utils.execute('ethtool', '-k', ifname)
        lines = output.split('\n')
        for line in lines:
            columns = line.split(":")
            if columns[0].strip() in FEATURES_LIST:
                if "on" in columns[1].strip():
                    features.append(FEATURES_MAP.get(columns[0].strip()))
        return {'name': devname,
                'capabilities': features}
