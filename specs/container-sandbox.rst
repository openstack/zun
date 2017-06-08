..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

=================
Container Sandbox
=================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/neutron-integration

Zun needs to manage containers as well as their associated IaaS resources,
such as IP addresses, security groups, ports, volumes, etc.. To decouple the
management of containers from their associated resources, we proposed to
introduce a new concept called ``sandbox``.

A sandbox represents an isolated environment for one or multiple containers.
The primary responsibility of sandbox is to provision and manage IaaS
resources associated with a container or a group of containers. In this model,
each container must have a sandbox, and resources (i.e. Neutron ports) are
attached to sandboxes (instead of directly being attached to containers).

The implementation of sandbox is driver-specific. Each driver needs to
implement the sandbox interface (as well as the container interface).
For docker driver, sandbox can be implemented by using docker container itself.
In this case, creating a container in Zun might create two docker containers
internally: a sandbox container and a 'real' container. The real container
might use the sandbox container as a proxy for networking, storage, or others.
Alternatively, users might create a container in an existing sandbox if they
don't want to create an extra sandbox.

Problem description
===================
Zun containers and Nova instances share the common needs for networking,
storage, scheduling, host management, quota management, and many others.
On the one hand, it is better to consolidate the management containers
and Nova instances to minimize the duplication, but on the other hand,
Zun needs to expose container-specific features that might go beyond the
Nova APIs.

To provide a full-featured container experience with minimized duplication
with Nova, an approach is to decouple the management of containers (implemented
in Zun) from management of other resources (implemented in Nova). This
motivates the introduction of sandbox that can be implemented as a docker
container provisioned by Nova. As a result, we obtain flexibility to offload
complex tasks to Nova.

Proposed change
===============
1. Introduce a new abstraction called ``sandbox``. Sandbox represents an
   isolated environment for one or multiple containers. All drivers are
   required to implement the sandbox abstraction with business logic to create
   and manage the isolated environment. For Linux container, an isolated
   environment can be implemented by using various Linux namespaces
   (i.e. pid, net, or ipc namespace).
2. For docker container, its sandbox could be implemented by using docker
   container itself. The sandbox container might not do anything real, but
   has one or multiple Neutron ports (or other resources) attached.
   The sandbox container is provisioned and managed by Nova (with a
   Zun-provided docker virt-driver). After the sandbox container is created,
   the real container can be created with the options
   ``--net=container:<sandbox>``, ``--ipc=container:<sandbox>``,
   ``--pid=container:<sandbox>`` and/or ``--volumes-from=<sandbox>``.
   This will create a container by joining the namespaces of the sandbox
   container so that resources in sandbox container can be shared.
3. The design should be extensible so that operators can plug-in their
   own drivers if they are not satisfied by the built-in sandbox
   implementation(s).

The diagram below offers an overview of the system architecture. The Zun
service may communicate with Nova to create a sandbox that is actually a
docker container. Like normal Nova instances, sandboxes are scheduled by Nova
scheduler and have Neutron ports attached for providing networking.
Containers are created by Zun, and run inside the namespaces of sandboxes.
Note that a sandbox can contain one or multiple containers. All containers
in a sandbox will be co-located and share the Linux namespaces of the sandbox.

::

                            +---------+
                            |   CLI   |
                            +----+----+
                                 |
                            +----+----+
 +-------- Nova -------+  +-+  REST   +----- Zun -----+
 |                     |  | +---------+               |
 |                     +--+                           |
 |                     |  |                           |
 +-----------+---------+  +---------------+-----------+
             |                            |
 +-----------|----+ Compute Host ---------|-----------+
 |    +------+-------+              +-----+-----+     |
 | +--+ Nova Compute +--+       +---+ Zun Agent +-+   |
 | |  +--------------+  |       |   +-----------+ |   |
 | |                    |       |                 |   |
 | |              +-----+-------|---+             |   |
 | |              |             |   |             |   |
 | +-- Sandbox -+ +-- Sandbox --|-+ +-- Sandbox --|-+ |
 | |            | |             | | |             | | |
 | |            | | +-----------+ | | +-----------+ | |
 | |            | | | Container | | | | Container | | |
 | |            | | +-----------+ | | +-----------+ | |
 | |            | |               | | +-----------+ | |
 | |            | |               | | | Container | | |
 | |            | |               | | +-----------+ | |
 | |            | |               | |               | |
 | +------------+ +---------------+ +---------------+ |
 |                                                    |
 +----------------------------------------------------+


Design Principles
-----------------
1. Minimum duplication between Nova and Zun. If possibly, reuse everything that
   has been implemented in Nova.
2. Similar user experience between VMs and containers. In particular, the ways
   to configure networking of a container should be similar as the VM
   equivalent.
3. Full-featured container APIs.


Alternatives
------------
1. Directly bind resources (i.e. Neutron ports) to containers. This will have a
   large amount of duplication between Nova and Zun.
2. Use Kuryr. Kuryr is designed for users who use native tool (i.e. docker
   CLI) to manage containers. In particular, what Kuryr provided to translate
   API calls to docker to API calls to Neutron. Zun doesn't expose native APIs
   to end-users so Kuryr cannot address Zun's use cases.


Data model impact
-----------------
Add a 'sandbox' table. Add a foreign key 'sandbox_id' to the existing table
'container'.


REST API impact
---------------
1. Add an new API endpoint /sandboxes to the REST API interface.
2. In the API endpoint of creating a container, add a new option to specify
   the sandbox where the container will be created from. If the sandbox is not
   specified, Zun will create a new sandbox for the container.


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
Performance penalty is expected since provisioning sandboxes take extra
compute resources. In addition, the Nova API will be used to create sandboxes,
which might also incur performance penalty.


Other deployer impact
---------------------
Deployers need to deploy a custom Nova virt-driver for provisioning sandboxes.


Developer impact
----------------
None


Implementation
==============


Assignee(s)
-----------

Primary assignee:
Hongbin Lu

Other contributors:


Work Items
----------
1. Implement a custom Nova virt-driver to provision sandboxes.
2. Implement a new API endpoint for sandboxes.
3. Implement unit/integration test.


Dependencies
============
Add a dependency to Nova


Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.
