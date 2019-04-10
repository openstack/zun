..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========================
Technical Vision for Zun
========================

This document is a self-evaluation of Zun with regard to the
Technical Committee's `technical vision`_.

.. _technical vision: https://governance.openstack.org/tc/reference/technical-vision.html

Mission Statement
=================

Zun's mission is to provide an OpenStack containers service that integrates
with various container technologies for managing application containers on
OpenStack.

Vision for OpenStack
====================

Self-service
------------

Zun are self-service. It provides users with the ability to deploy
containerized applications on demand without having to wait for human action.
Zun containers are isolated between tenants. Containers controlled by
one tenant are not accessible by other tenants.
Quotas are used to limit the number of containers or compute resources
(i.e. CPU, RAM) within a tenant.

Application Control
-------------------

Zun allows application control of containers by offering RESTful API,
CLI, and Python API binding. In addition, there are third-party tools
like `Gophercloud`_ that provide API binding for other programming
languages. The access of Zun's API is secured by Keystone so
applications that are authenticatable with Keystone can access Zun's API
securely.

.. _Gophercloud: https://github.com/gophercloud/gophercloud

Interoperability
----------------

Zun containers (and other API resources) are designed to be deployable and
portable across a variety of public and private OpenStack clouds.
Zun's API hides differences between container engines and
exposes standard container abstraction.

Bidirectional Compatibility
---------------------------

Zun implements `API microversion`_.
API consumers can query the min/max API version that an OpenStack cloud
supports, as well as pinning a specific API version to guarantee consistent
API behavior across different versions of OpenStack.

.. _API microversion: https://docs.openstack.org/zun/latest/reference/api-microversion-history.html

Cross-Project Dependencies
--------------------------

Zun depends on Keystone for authentication, Neutron for container networks,
Cinder for container volumes. Zun aims to integrate with Placement for
tracking compute resources and retrieving allocation candidates.
Therefore, Placement is expected to be another dependency of Zun
in the near future.

Partitioning
------------

It is totally fine to deploy Zun in multiple OpenStack regions,
and each region could have a Zun endpoint in Keystone service catalog.
Zun also supports the concept of 'availability zones' - groupings within
a region that share no common points of failure.

Basic Physical Data Center Management
-------------------------------------

Zun interfaces with external systems like Docker engine, which
consumes compute resources in data center and offers compute
capacity to end-users in the form of containers.
Zun APIs provide a consistent interface to various container technologies,
which can be implemented by different Open Source projects.

Hardware Virtualisation
-----------------------

Similar to Nova, Zun also aims to virtualize hardware resources
(essentially physical servers) and provide them to users via a
vendor-independent API. The difference is that Zun delivers
compute resources in the form of containers instead of VMs.
Operators have a choice of container runtimes which could be
a hypervisor-based runtime (i.e. Kata Container) or a traditional
runtime (i.e. runc). The choice of container runtime is a trade-off
between tenant isolation and performance.

Plays Well With Others
----------------------

Zun plays well with Container Orchestration Engines like Kubernetes.
In particular, there is an `OpenStack provider`_ for Virtual Kubelet,
which mimics Kubelet to register itself as a node in a Kubernetes cluster.
The OpenStack provider leverages Zun to launch container workloads that
Kubernetes schedules to the virtual node.

.. _OpenStack provider: https://github.com/virtual-kubelet/virtual-kubelet/tree/master/providers/openstack

Infinite, Continuous Scaling
----------------------------

Zun facilitates infinite and continuous scaling of applications.
It allows users to scale up their applications by spinning up containers
on demand (without pre-creating a container host or cluster).
Containers allow sharing of physical resources in data center at a more
fine-grained level than a VM thus resulting in a better utilization of
resources.

Built-in Reliability and Durability
-----------------------------------

Unlike VMs, containers are usually transient and allowed to be deleted
and re-created in response to failure.
In this context, Zun aims to provide primitives for deployers
to deploy a highly available applications. For example, it allows deployers
to deploy their applications across different availability zones.
It supports health check of containers so that orchestrators can quickly
detect failure and perform recover actions.

Customizable Integration
------------------------

Zun is integrated with Heat, which allows users to 'wire' containers
with resources provided by other services (i.e. networks, volumes,
security groups, floating IPs, load balancers, or even VMs).
In addition, the Kubernetes integration feature provides another option
to 'wire' containers to customize the topology of application deployments.

Graphical User Interface
------------------------

Zun has a Horizon plugin, which allows users to consume Zun services
through a graphical user interface provided by Horizon.
