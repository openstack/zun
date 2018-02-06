..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

===============================
PCI passthrough device modeling
===============================

Related Launchpad Blueprint:
https://blueprints.launchpad.net/zun/+spec/container-pci-device-modeling

PCI passthrough enables full access and direct control of a physical PCI
device in a Zun container. With PCI passthrough, the full physical device
is assigned to only one container and cannot be shared. This mechanism is
generic for any kind of PCI devices. For example, it runs with a Network
Interface Card (NIC), Graphics Processing Unit (GPU), or any other devices
that can be attached to a PCI bus. To properly use the devices, containers
are required to install the correct driver of the device.

Some PCI devices provide Single Root I/O Virtualization and Sharing (SR-IOV)
capabilities to share the PCI device among different VMs or containers. When
SR-IOV is used, a physical device is virtualized and appears as multiple PCI
devices. Virtual PCI devices are assigned to the same or different containers.

Since release Ocata, Openstack Nova enables flavor-based PCI-passthough device
management. This design will not depend on the Nova's implementation of PCI-
passthough work. However the design and implementation in Zun will refer to
the existing of Nova work and try to be consistent with Nova's implementation.

Problem description
===================
Currently, Zun scheduler can only schedule work loads with requests of regular
compute resources, such as CPUs, RAMs. There are some emerging use cases
requiring containers to access resources such as GPUs, NICs and so on. PCI
passthrough and SR-IOV are the common technology to enable such use cases.
To support the new use cases, the new resources will be added to Zun compute
resource model, and allow Zun scheduler to place the work load according to
the availability of the resources.

Proposed change
===============
1. Introduce a new configuration to abstract the PCI devices at Zun Compute.
   A new PCI passthrough whitelist configuration will allow cloud
   administrators to explicitly define a list PCI devices to be available
   for Zun Compute services. The whitelist of PCI devices should be common
   for both network PCI devices and other compute or storage PCI devices.
   The PCI whitelist can be implemented exactly as Nova[1]:
   In zun.conf, whitelist entries are defined as the following:

::

     pci_passthrough_whitelist = {<entry>}
     Each whitelist entry is defined in the format:
        ["vendor_id": "<id>",]
        ["product_id": "<id>",]
        ["address": "[[[[<domain>]:]<bus>]:][<slot>][.[<function>]]" |
         "devname": "PCI Device Name",]
        ["tag":"<tag_value>",]

   The valid key values are:
       "vendor_id": Vendor ID of the device in hexadecimal.
       "product_id": Product ID of the device in hexadecimal.
       "address": PCI address of the device.
       "devname": Device name of the device (for e.g. interface name). Not all
               PCI devices have a name.
       "<tag>": Additional <tag> and <tag_value> used for matching PCI devices.
             Supported <tag>: "physical_network". The pre-defined tag
             "physical_network" is used to define the physical network, that
             the SR-IOV NIC devices are attached to.

2. Introduce a new configuration pci alias to allow zun to specify the PCI
   device without needing to repeat all the PCI property requirement.
   For example,

::

    alias = {
        "name": "QuickAssist",
        "product_id": "0443",
        "vendor_id": "8086",
        "device_type": "type-PCI"
    }

   defines an alias for the Intel QuickAssist card. Valid key values are
    "name": Name of the PCI alias.
    "product_id": Product ID of the device in hexadecimal.
    "vendor_id": Vendor ID of the device in hexadecimal.
    "device_type": Type of PCI device. Valid values are: "type-PCI",
                   "type-PF" and "type-VF".

The typical workflow will be as following:

1. A cloud admin configures PCI-PASSTHROUGH alias at /etc/zun.conf on the
   openstack controller nodes.

::

    [default]
    pci_alias = {
        "name": "QuickAssist",
        "product_id": "0443",
        "vendor_id": "8086",
        "device_type": "type-PCI"
    }

2. Cloud admin enables the PCI-PASSTHROUGH filter to /etc/zun.conf at
   openstack controller nodes.

::

    scheduler_available_filters=zun.scheduler.filters.all_filters
    scheduler_default_filters= ..., PciPassthroughFilter

3. Cloud admin restarts the Zun-API service to make the configuration
   effective;
4. Cloud admin adds available PCI Passthrough devices to the whitelist of
   /etc/zun.conf at Zun compute nodes. An example can be the following:

::

    [default]
    pci_passthrough_whitelist = {
        "product_id": "0443",
        "vendor_id": "8086",
        "device_type": "type-PCI",
        "address": ":0a:00."
    }
   All PCI devices matching the vendor_id and product_id are added to the pool
   of PCI devices available for passthrough to Zun containers.

5. Cloud admin restarts Zun Compute service to make the configuration
   effective.
6. Each Zun Compute service updates the PCI-Passthough devices' availability to
   Zun Scheduler perioadially.
7. Cloud user creates a new container with request of a PCI-Passthrough
   device. For example, the following command will create a test_QuickAssist
   container with two PCI devices named "QuickAssist" attached. The design and
   implementation details of creating a workload with PCI_Passthrough devices
   are out of the scope of this design spec. Please refer to the other
   blueprints (TBD) for more details.

    $ zun create --pci_passthrough QuickAssist:1 test_QuickAssist

Alternatives
------------
It is a more desirable way to define workloads using flavors. PCI-Passthough
configurations, in particularly pci_alias can be included in the flavor
configuration [2][3]. Thus users will use the flavor to specify the PCI device
to be used for container.
Integration with OpenStack Cyborg is another mid to long term alternative[4].
Cyborg as a service for managing accelerators of any kind needs to cooperate
with Zun on two planes: first, Cyborg should inform Zun about the resources
through placement API[5], so that scheduler can leverage user request for
particular functionality into assignment of specific resource using resource
provider which possess an accelerator; second, Cyborg should be able to provide
information how Zun compute can attach particular resource to containers.

Data model impact
-----------------
- Introduce a new object list pci-alias, which is a list of alias object:

::

    fields = {
        "name" : fields.StringField(nullable=False),
        "vendor_id": fields.StringField(nullable=False),
        "product_id": fields.StringField(nullable=False),
        "device_type": fields.StringField(nullable=False)
    }

- Introduce a new field in the container object called 'pci-alias-usage',
    for example:
        "pci_alias_name": fields.StringField(nullable=False),
        "count": fields.IntField(nullable=True)

- Add pci-devices to the compute_node object. Each pci-device should have
  the following fields as an example:

::

    {
        "vendor_id": fields.StringField(nullable=False),
        "product_id": fields.StringField(nullable=False),
        "address": fields.StringField(nullable=True),
        "devname": fields.StringField(nullable=True),
        "physical_network": fields.StringField(nullable=True),
    }

REST API impact
---------------
None

Security impact
---------------
None

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


Assignee(s)
-----------

Primary assignee:

Other contributors:


Work Items
----------
1. Implement codes to read and validate pci_alias configuration;
2. Implement codes to read and validate pci_whitelist configuration;
3. Implement new pci-alias model and the verify if a pci_alias match
   a given pci_whitelist entry upon a new zun compute service available;
4. Implement unit/integration test.

Dependencies
============
The full function of enable Pci passthrough will depend on other component
in Zun or outside of Zun such as Neutron and Kuryr;
Support GPU PCI-PASSTHROUGH will require the support of NVIDIA docker run-time;
Support SR-IOV NIC PCI-PASSTHROUGH will require SR-IOV port binding from Kuryr.

Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.

References
==========
[1] https://docs.openstack.org/nova/latest/admin/pci-passthrough.html

[2] PCI flavor-based device assignment https://docs.google.com/
    document/d/1vadqmurlnlvZ5bv3BlUbFeXRS_wh-dsgi5plSjimWjU

[3] https://wiki.openstack.org/wiki/PCI_passthrough_SRIOV_support

[4] https://review.openstack.org/#/c/448228/

[5] https://docs.openstack.org/nova/latest/user/placement.html
