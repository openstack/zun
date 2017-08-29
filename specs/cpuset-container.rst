..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

==========================
Supporting CPU sets in ZUN
==========================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/cpuset-container

ZUN presently does not have a way to allow users to specify dedicated
resources for workloads that require higher performance. Such workloads
can be classified as Network Function Virtualization (NFV) based, AI
based or HPC based. This spec takes a first step towards supporting
such workloads with dedicated resources. The first of such resources
can be the cpusets or cores on a given physical host.



Problem description
===================

Exposing cpusets to the cloud users cannot be done in its raw form.
This is because, exposing such parameters to the end user breaks
the cloudy model of doing things.

Exposing cpusets can be broadly thought of as combination of user policies
and host capabilities.

The user policies are applied against compute host capabilities and if it
matches, the user is allowed to perform the CRUD operations on a container.

Proposed change
===============
1. Piggy back on the work done for host capabilities.

More details of this work would be covered on a separate blueprint:
https://blueprints.launchpad.net/zun/+spec/expose-host-capabilities

2. Hydrate the schema with information obtained via calling driver specific
methods that obtain the details of a host inventory. For cpusets, lscpu -p
can be used to obtain the required information. Implement a periodic task
that inventories the host at regular intervals.

3. Define 2 user cpu-policies called "dedicated" and "shared". The first
policy signifies that the user wants to use dedicated cpusets for their
workloads. The shared mode is very similar to the default behavior. If unless
specified, the behavior will be defaulted to "shared".

4. Write driver methods to provision containers with dedicated cpusets.
The logic of 'what' cpusets should be picked up for a given requests lies
in the control of the zun code and is not exposed to the user.

5. The cpu-policy parameter is specified in conjunction with the vcpus field
for container creation. The number of vcpus shall determine the number of
cpusets requested for dedicated usage.

6. If this feature is being used with the zun scheduler, then the scheduler
needs to be aware of the host capabilities to choose the right host.

For example::

  $ zun run -i -t --name test --cpu 4 --cpu-policy dedicated

We would try to support scheduling using both of these policies on the same
host.

How it works internally?

Once the user specifies the number of cpus, we would try to select a numa node
that has the same or more number of cpusets unpinned that can satisfy
the request.

Once the cpusets are determined by the scheduler and it's corresponding numa
node, a driver method should be called for the actual provisoning of the
request on the compute node. Corresponding updates would be made to the
inventory table.

In case of the docker driver - this can be achieved by a docker run
equivalent::

  $ docker run -d ubuntu --cpusets-cpu="1,3" --cpuset-mems="1,3"

The cpuset-mems would allow the memory access for the cpusets to
stay localized.

If the container is in paused/stopped state, the DB will still continue to
block the pinset information for the container instead of releasing it.


Design Principles
-----------------
1. Build a host capability model that can be leveraged by the zun scheduler.

2. Create abstract user policies for the cloud user instead of raw
values.


Alternatives
------------
None


Data model impact
-----------------
- Introduce a new field in the container object called 'cpu_policy'.
- Add a new numa.py object to store the inventory information.
- Add numa topology obtained to the compute_node object.


REST API impact
---------------
The existing container CRUD APIs should allow a new parameter
for cpu policy.

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
Sudipta Biswas (sbiswas7@in.ibm.com)

Other contributors:
Hongbin Lu, Pradeep Singh

Work Items
----------
1. Create the new schema.
2. Add cpu_policy field in the REST APIs and zun client.
3. Write logic to hydrate the inventory tables.
4. Implement a periodic task that inventories the host.
5. Write logic to check the cpusets of a given host.
6. Implement unit/integration test.


Dependencies
============

Testing
=======
Each patch will have unit tests.


Documentation Impact
====================
A set of documentation for this new feature will be required.
