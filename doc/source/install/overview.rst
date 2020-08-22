========
Overview
========

The Container service provides OpenStack-native API for launching and managing
application containers without any virtual machine managements.

Also known as the ``zun`` project, the OpenStack Container service may,
depending upon configuration, interact with several other OpenStack services.
This includes:

- The OpenStack Identity service (``keystone``) for request authentication and
  to locate other OpenStack services
- The OpenStack Networking service (``neutron``) for DHCP and network
  configuration
- The Docker remote network driver for OpenStack (``kuryr-libnetwork``)
- The OpenStack Placement service (``placement``) for resource tracking and
  container allocation claiming.
- The OpenStack Block Storage (``cinder``) provides volumes for container
  (optional).
- The OpenStack Image service (``glance``) from which to retrieve container
  images (optional).
- The OpenStack Dashboard service (``horizon``) for providing the web UI
  (optional).
- The OpenStack Orchestration service (``heat``) for providing orchestration
  between containers and other OpenStack resources (optional).

Zun requires at least two nodes (Controller node and Compute node) to run
a container. Optional services such as Block Storage require additional nodes.

Controller
----------

The controller node runs the Identity service, Image service, management
portions of Zun, management portion of Networking, various Networking
agents, and the Dashboard. It also includes supporting services such as an SQL
database, message queue, and Network Time Protocol (NTP).

Optionally, the controller node runs portions of the Block Storage, Object
Storage, and Orchestration services.

The controller node requires a minimum of two network interfaces.

Compute
-------

The compute node runs the engine portion of Zun that operates containers.
By default, Zun uses Docker as container engine. The compute node also runs
a Networking service agent that connects containers to virtual networks and
provides firewalling services to instances via security groups.

You can deploy more than one compute node. Each node requires a minimum of two
network interfaces.
