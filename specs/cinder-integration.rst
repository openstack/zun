..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

============================
Container Cinder Integration
============================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/cinder-zun-integration

Zun needs to manage containers as well as their associated IaaS resources,
such as IP addresses, security groups, ports, volumes, etc.
Zun containers should be able to use volumes which has multiple storage
vendors or plugins support.

As zun is project belongs to OpenStack ecosystem and zun has integration
with Cinder which is block storage service.

Fuxi is new OpenStack project which aims to integrate Cinder to docker
volumes. With Fuxi, Cinder can be used as the unified persistence storage
provider for virtual machine, baremetal and Docker container.

The implementation of Cinder is enabled using fuxi driver from zun. We need
to implement Cinder driver in Zun which manages volumes, let Fuxi control the
mount/unmount volume from Docker container.

Problem description
===================
To store some large amount data in container is not possible. In case of
of containers, all the storage resides in host storage which is not good
solution. If host goes down, storage wont be accessible.
We need to somehow use cloud storage, which is reliable and we can attach
it to container so that people use containers for workloads also.

Proposed change
===============
There are two approaches docker provides to add volume to Container.

1. Using Docker run

docker run -d --volume-driver= Fuxi -v my-named-volume --name web_app

2. Create volume first & then add it to Container

docker volume create --driver fuxi
                        --name test_vol
                        -o size=1
                        -o fstype=ext4
                        -o multiattach=true

docker run -d -v my-named-volume
                        --name web_app

I think, we can support both

1. To Implement first approach, we need following changes
* Introduce fields in Container API -  volume-driver, vol-name, vol-size.
* We pass call to Volume Driver to create volume.
* Volume driver connects to Cinder & handles volume creation.
* Once volume is created in Cinder, then we finally go add volume-driver
as Fuxi & add volume name which created in cinder.
* Fuxi should be installed in Docker host and configured with Cinder engine.

2. To Implement Second approach, we need following changes
* Introduce Volume API in Zun which has fields volume-driver, volume-name,
volume-size etc.
* Volume API will connect to volume driver which will sit under
/zun/volume/driver.py.
* Volume Driver connects to Cinder and handles volume creation in Cinder.
* Once the volume is created in Cinder, it communicates to Docker Volume API
to attach the created volume in Docker.
* Docker Volume API use --driver=Fuxi which goes talks to Cinder and attach
created Volume in Docker.
* Prerequisite here is, Fuxi should be installed on docker host & configured
with Cinder. If not, it returns the 500 response.
* Also we need to introduce new Volume table which contains field vol-driver,
vol-name, vol-size fields.
* We need to add storage section in conf file, where we can specify some
default attributes like storage engine Cinder, Cinder endpoint etc.
* We also need to configure Cinder endpoint in Fuxi conf file.
* We can use same implementation for Flocker also as it supports Cinder.
* I think if we can create separate CinderDriver which calls from Volume
volume driver. This approach enables way to implement multiple storages
supports in the future and we can plug-in multiple storage implementation.

The diagram below offers an overview of the system architecture. The Zun
service may communicate with Fuxi and fuxi talks to Cinder for volumes.

::

                          +---------+
                          |   CLI   |
                          +----+----+
                               |
                          +----+----+
                 |+-+ REST +----- Zun ----+|
                 |+--                   --+|
                 |+------------+----------+|
                               |
 |+--------------------+ Volume Driver+-------------+|
 ||              |                  |                |
 ||              |                  |                |
 ||              |                  |                |
 ||       +-----------+    +---------------+         |
 ||       | Cinder    |    | Docker Volume |         |
 ||       +-----------+    +---------------+         |
 ||                         |            |           |
 ||                    +---------+    +-----------+  |
 ||                    |   Fuxi  |    |   Flocker |  |
 ||                    +----+----+    +-----------+  |
 |+------------+ +---------------+ +----------------+|
 |                                                   |
 +---------------------------------------------------+


Design Principles
-----------------
1. Similar user experience between VMs and containers. In particular, the ways
   to configure volumes of a container should be similar as the VM equivalent.
2. Full-featured container APIs.


Alternatives
------------
1. We can use rexray for storage support, its again third party tool which
   increases the dependency.

Data model impact
-----------------
Add volume-driver, vol-name, size field in the Volume Table.
Need to add volume_id to Container Table.


REST API impact
---------------
We need to add below APIs
1. Create a volume - POST /v1/volumes
2. List volumes - GET /v1/volumes
3. Inspect volume - GET /v1/volumes/<uuid>
4. Delect Volume - DELETE /v1/volumes/<uuid>

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
Deployers need to deploy a Fuxi and Cinder.


Developer impact
----------------
None


Implementation
==============


Assignee(s)
-----------

Primary assignee:
Digambar

Other contributors:


Work Items
----------
1. We need to introduce new Volume API.
2. Implement volume driver in zun.
3. Implement Cinder calls under the volume driver.
4. Implement Docker volume support in Zun.
5. Add volume section in zun.conf.
6. Add volume-driver support in CLI.
7. Implement unit/integration test.


Dependencies
============
Add a dependency to Cinder.


Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.
