..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

===========================
Container SR-IOV networking
===========================

Related Launchpad Blueprint:
https://blueprints.launchpad.net/zun/+spec/container-sr-iov-networking


Problem description
===================
SR-IOV (Single-root input/output virtualization) is a technique that allows
a single physical PCIe (Peripheral Component Interconnect Express) device
to be shared across several clients (VMs or containers). SR-IOV networking
allows Nova VMs and containers access to virtual networks via SR-IOV NICs.
Each such SR-IOV NIC would have a single PF (Physical Function) and multiple
VFs (Virtual Functions). Essentially the PF and VFs appears as multiple PCIe
SR-IOV based NICs. With SR-IOV networking, the traditional virtual bridge is
no longer required, and thus higher networking performance can be achieved.
This is an important requirement for most Virtualized Network Functions (VNFs).
To support VNF application deployment over Zun containers, it is desirable to
support SR-IOV networking feature for Zun.

To enable SR-IOV networking for Zun containers, Zun should provide a data
model for PCI passthrough devices, and a filter to enable Zun scheduler
locate the Zun computes that have access to the PCI passthrough devices.
These two dependencies are addressed under separated blueprint[1][2].

Kuryr driver is used for Zun container networking. Kuryr implements a
libnetwork remote network driver and maps its calls to OpenStack Neutron.
It works as a translator between libnetwork's Container Network Model (CNM)
and Neutron's networking model. Kuryr also acts as a libnetwork IPAM driver.
This design will try to use the existing functions provided by Kuryr and
identify the new requirements for Kuryr and Zun for the SR-IOV support.

With Kuryr driver, Zun will implement SR-IOV networking following the
procedure below:

- Cloud admin enables PCI-passthrough filter at /etc/zun.conf [1];
- Cloud admin creates a new PCI-passthrough alias [2];
- Cloud admin configures PCI passthrough whitelist at Zun compute [2];
- Cloud admin enables sriovnicswitch on Neutron server (with existing Neutron
  support)[3];
- Cloud admin configures supported_pci_vendor_devs at
  /etc/neutron/plugins/ml2/ml2_conf_sriov.ini (with existing Neutron
  support)[3];
- Cloud admin configures sriov_nic.physical_device_mappings at
  /etc/neutron/plugins/ml2/ml2_conf_sriov.ini on Zun compute nodes (with
  existing Neutron support)[3];
- Cloud admin creates a network that SR-IOV NIC connects (with existing
  Neutron support)[3];
- Cloud user creates a SR-IOV network port with an IP address (with existing
  Neutron support)[3]; Usually, the IP address is optional for creating a
  Neutron port. But Kuryr currently (in release Ocata) only support matching
  IP address to find the Neutron port that to be used for a container, thus
  IP address becomes a mandatory parameter here. This limitation will be
  removed once Kuryr can take neutron port-id as input.
- Cloud user creates a new container bound with the SR-IOV network port.

This design spec focuses on the last step above.

Proposed change
===============
1. Introduce a new option to allow user specify the neutron port-id when zun
   creates a container, for example:

       zun create --name container_name --nets port=port_uuid ...

   For a neutron SR-IOV port, the vnic_type attribute of the port is "direct".
   Ideally, kuryr_libnetwork should use the vnic_type to decide which port
   driver will be used to attach the neutron port to the container. However,
   kuryr can only support one port driver per host with current Ocata release.
   This means if we enable new SR-IOV port driver through the existing
   configuration at kuryr.conf, zun can only create containers using SR-IOV
   ports on the host. We expect kuryr will remove this limitation in the
   future.

2. Implement a new sriov_port_driver at kuryr_libnetwork.

   The sriov_port_driver implements the abstract function create_host_iface().
   The function allocates an SR-IOV VF on the host for the specified neutron
   port (e.g. pass-in parameter). Then the port is bound to the corresponding
   network subsystem[5].

   The sriov_port_driver should also implement delete_host_iface(). The
   function de-allocates the SR-IOV VF and adds it back to the available VF
   pool.

   The sriov_port_driver also implements get_container_iface_name(). This
   function should return the name of the VF instance.

   Once a SR-IOV network port is available, Docker will call kuryr-libnetwork
   API to bind the neutron port to a network interface attached to the
   container. The name of the allocated VF instance will be passed to
   Docker[6]. The VF interface name representing the actual OS level VF
   interface that should be moved by LibNetwork into the sandbox[7].

Alternatives
------------
Two other alternatives have been considered for the design. But both options
requires significant changes in existing Kuryr implementations. The above
design is believed to have minimum impact on Kuryr.

Option-1:

   Zun creates containers with pre-configured SR-IOV port, and also manages
   the VF resources. This design option is very similar to the proposed
   design. The only difference is that VFs are managed or allocated by Zun.
   Zun then pass the VF name to Kuryr. The potential benefit of this option
   is to reuse all (PCI-passthrough and SR-IOV) resource management functions
   to be implemented for non-networking application.

Option-2:

   Zun creates containers with both network and SR-IOV networking option.
   Kuryr driver will integrate with Docker SR-IOV driver[8] and create Docker
   network with SR-IOV VF interfaces as needed. This design offloads the SR-IOV
   specific implementation to the Docker SR-IOV driver, but at same time
   introduce additional work to integrate with the driver. With this design,
   the VF resources are managed by the Docker SR-IOV driver.


Data model impact
-----------------
Refer to [2].

REST API impact
---------------
The proposed design relies an API change in container creation. The change
allows user to specify an pre-created neutron port to be used for the
container. The implementation of the change is in progress[9].
The existing container CRUD APIs will allow a set of new parameters for
neutron networks with port-ID, for example:

::

    "nets": [
        {
            "v4-fixed-ip": "",
            "network": "",
            "v6-fixed-ip": "",
            "port": "890699a9-4690-4bd6-8b70-3a9c1be77ecb"
        }
    ]

Security impact
---------------
Security group feature are not supported on SR-IOV ports. The same limitation
applies to SR-IOV networking with Nova virtual machines.

Notifications impact
--------------------
None

Other end user impact
---------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None


Implementation
==============
1. Change the networking option to allow port as an option when creating
   containers;
2. Implement sriov_port_driver at kuryr-libnetwork

Assignee(s)
-----------
Primary assignee:
TBD

Other contributors:
Bin Zhou
Hongbin Lu

Work Items
----------
Implement container creation with existing neutron port[9].


Dependencies
============
SR-IOV port driver implementation at Kuryr-libnetwork.


Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A user guide will be required to describe the full configurations and
operations.


References
==========
[1] https://blueprints.launchpad.net/zun/+spec/container-pci-device-modeling

[2] https://blueprints.launchpad.net/zun/+spec/support-pcipassthroughfilter

[3] https://wiki.openstack.org/wiki/SR-IOV-Passthrough-For-Networking

[4] https://docs.openstack.org/kuryr-libnetwork/latest/devref/libnetwork_remote_driver_design.html

[5] https://github.com/openstack/kuryr-libnetwork/tree/master/kuryr_libnetwork/port_driver

[6] https://github.com/openstack/kuryr-libnetwork/blob/master/kuryr_libnetwork/controllers.py

[7] https://github.com/Docker/libnetwork/blob/master/docs/remote.md#join

[8] https://github.com/Mellanox/Docker-passthrough-plugin

[9] https://review.openstack.org/481861
