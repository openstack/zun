..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
Kuryr Integration
=================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/kuryr-integration

Zun provides APIs for managing application containers, and the implementation
of the APIs is provided by drivers. Currently, Zun has two built-in drivers:
the native Docker driver and the Nova Docker driver. The Nova driver leverages
existing Nova capability to provide networking for containers. However, the
native Docker driver doesn't have an ideal solution for networking yet.

This spec proposed to leverage Kuryr-libnetwork [1] for providing networking
for containers. Generally speaking, Kuryr-libnetwork is a remote Docker
networking plugin that receives requests from Docker engine and interfaces
with Neutron for managing the network resources. Kuryr-libnetwork provides
several features, such as IPAM, Neutron port binding, etc., all of which
could be leveraged by Zun.

Problem description
===================
Currently, the native Docker driver doesn't integrate with Neutron. It uses
the default networking capability provided by Docker engine. Containers
created by that driver has limited networking capabilities, and they
are not able to communicate with other OpenStack resources (i.e. Nova
instances).

Proposed change
===============
1. Introduce a network abstraction in Zun. Implement an API for users to
   create/delete/manage container networks backed by Kuryr. If the container
   runtime is Docker, creating a container network will call docker network
   APIs to create a Docker network by using the pre-created Neutron resources
   (this capability is provided by Kuryr [2][3]). Deleting a container network
   will be similar as create.
2. Support creating a container from a network. If a user specifies a network
   on creating a container, the container will be created from the network.
   If not, the driver will take care the networking of the container. For
   example, some drivers might choose to create the container from a default
   network that might be specified in a config file or hard-coded. It is up to
   individual driver to decide how to create a container from a network.
   On the Zun's Docker driver, this is implemented by adding --net=<ID> option
   when creating the sandbox [4] of the container.

The typical workflow will be as following:

1. Users call Neutron APIs to create a Neutron network.

       $ neutron net-create testnet

2. Users call Neutron APIs to create a Neutron subnetpool.

       $ neutron subnetpool-create --pool-prefix 10.2.0.0/16 testpool

3. Users call Neutron APIs to create a Neutron subnet.

       $ neutron subnet-create --subnetpool testpool \
                               --name testsubnet \
                               testnet 10.2.0.0/24

4. Users call Zun APIs to create a container network.

       $ zun network-create --neutron-net testnet \
                            --neutron-pool testpool \
                            --neutron-subnet testsubnet \
                            foo

5. Under the hood, Zun call Docker APIs to create a Docker network. This is
   equivalent to:

       $ docker network create -d kuryr --ipam-driver=kuryr \
             --subnet 10.2.0.0/24 --gateway 10.2.0.1 \
             -o neutron.net.uuid=<uuid_of_testnet> \
             -o neutron.pool.uuid=<uuid_of_testpool> \
             --ipam-opt neutron.pool.uuid=<uuid_of_testpool> \
             foo

NOTE: In this step, docker engine will check the list of registered network
plugin and find the API endpoint of Kuryr, then make a call to Kuryr to create
a network with existing Neutron resources (i.e. testnet, testpool, etc.).
It is assumed that the Neutron resources are pre-created by users at
their tenants (as shown at step 1-3). That is for walking around the limitation
that Kuryr can only create resources at single tenant.

6. Users call Zun APIs to create a container from the network.

       $ zun run --net=foo nginx

7. Zun call Docker APIs to create the container and its sandbox. This is
   equivalent to:

       $ docker run --net=foo kubernetes/pause --name sandbox
       $ docker run --net=container:sandbox nginx

NOTE: In the first command, docker engine will make a call to Kuryr to setup
the networking of the sandbox container. Kuryr will handle all the steps
to network the container (i.e. create a Neutron port, perform a port-binding,
etc.).

8. Users calls Zun API to list/show the created network(s).

       $ zun network-list
       $ zun network-show foo

9. Upon completion, users calls Zun API to remove the container and network.

       $ zun delete <container_id>
       $ zun network-delete foo


Alternatives
------------
1. Directly integrate with Neutron (without Kuryr-libnetwork). This approach
   basically re-invented Kuryr functionalities in Zun, which is unnecessary.
2. Use alternative networking solution (i.e. Flannel) instead of Neutron.
   This doesn't provide a good OpenStack integration.


Data model impact
-----------------
* Create a 'network' table. Each entry in this table is a record of a network.
  A network must belong to an OpenStack project so there will be a 'project_id'
  column in this table.
* Create a 'network_attachment' table. Each entry in this table is a record of
  an attachment between a network and a container. In fact, this table defines
  a many-to-many relationship between networks and containers.


REST API impact
---------------
1. Add a new API endpoint /networks to the REST API interface.
2. In the API endpoint of creating a container, add a new option to specify
   the network where the container will be created from.


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
Deployers need to deploy a Kuryr-libnetwork as a prerequisites of using this
feature.


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
Sudipta Biswas


Work Items
----------
1. Implement a new API endpoint for networks.
2. Extend the Docker driver to support creating containers from a network.
3. Implement unit/integration test.
4. Document the new network API.


Dependencies
============
Add a dependency to Kuryr-libnetwork and Neutron


Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.

References
==========
[1] https://github.com/openstack/kuryr-libnetwork
[2] https://blueprints.launchpad.net/kuryr/+spec/existing-neutron-network
[3] https://blueprints.launchpad.net/kuryr-libnetwork/+spec/existing-subnetpool
[4] https://github.com/openstack/zun/blob/master/specs/container-sandbox.rst
