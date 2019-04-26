..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

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

1. Users call Zun APIs to create a container network by passing a name/uuid of
   a neutron network::

    $ zun network-create --neutron-net private --name foo

2. After receiving this request, Zun will make several API calls to Neutron
   to retrieve the necessary information about the specified network
   ('private' in this example). In particular, Zun will list all the subnets
   that belong to 'private' network. The number of subnets under a network
   should only be one or two. If the number of subnets is two, they must be
   an ipv4 subnet and an ipv6 subnet respectively. Zun will retrieve the
   cidr/gateway/subnetpool of each subnet and pass these information to
   Docker to create a Docker network. The API call will be similar to::

    $ docker network create -d kuryr --ipam-driver=kuryr \
                      --subnet <ipv4_cidr> \
                      --gateway <ipv4_gateway> \
                      -ipv6 --subnet <ipv6_cidr> \
                      --gateway <ipv6_gateway> \
                      -o neutron.net.uuid=<network_uuid> \
                      -o neutron.pool.uuid=<ipv4_pool_uuid> \
                      --ipam-opt neutron.pool.uuid=<ipv4_pool_uuid> \
                      -o neutron.pool.v6.uuid=<ipv6_pool_uuid> \
                      --ipam-opt neutron.pool.v6.uuid=<ipv6_pool_uuid> \
                      foo

NOTE: In this step, docker engine will check the list of registered network
plugin and find the API endpoint of Kuryr, then make a call to Kuryr to create
a network with existing Neutron resources (i.e. network, subnetpool, etc.).
This example assumed that the Neutron resources were pre-created by cloud
administrator (which should be the case at most of the clouds). If this is
not true, users need to manually create the resources.

3. Users call Zun APIs to create a container from the container network 'foo'::

    $ zun run --net=foo nginx

4. Under the hood, Zun will perform several steps to configure the networking.
   First, call neutron API to create a port from the specified neutron
   network::

    $ neutron port-create private

5. Then, Zun will retrieve information of the created neutron port and retrieve
   its IP address(es). A port could have one or two IP addresses: an ipv4
   address and/or an ipv6 address. Then, call Docker APIs to create the
   container by using the IP address(es) of the neutron port. This is
   equivalent to::

    $ docker run --net=foo kubernetes/pause --ip <ipv4_address> \
                                            --ip6 <ipv6_address>

NOTE: In this step, docker engine will make a call to Kuryr to setup the
networking of the container. After receiving the request from Docker, Kuryr
will perform the necessary steps to connect the container to the neutron port.
This might include something like: create a veth pair, connect one end of the
veth pair to the container, connect the other end of the veth pair a
neutron-created bridge, etc.

6. Users calls Zun API to list/show the created network(s)::

    $ zun network-list
    $ zun network-show foo

7. Upon completion, users calls Zun API to remove the container and network::

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
[1] https://opendev.org/openstack/kuryr-libnetwork

[2] https://blueprints.launchpad.net/kuryr/+spec/existing-neutron-network

[3] https://blueprints.launchpad.net/kuryr-libnetwork/+spec/existing-subnetpool

[4] https://opendev.org/openstack/zun/src/branch/master/specs/container-sandbox.rst
