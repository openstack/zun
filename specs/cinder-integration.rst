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

As Zun is project belongs to OpenStack ecosystem and Zun has integration
with Cinder which is block storage service.

Problem description
===================
Data persistence in container is infeasible. The root file system of a Docker
container is a Union File System. Data resides in Union File System is
ephemeral because the data will lose whenever the container is deleted or
the host goes down. In addition, the performance of persisting a large amount
of data into Union File System is suboptimal.

To address the use cases that require persisting a large amount of data,
a common solution is to leverage the Docker data volume. A data volume is a
specially-designated directory within one or more containers that bypasses
the Union File System [1]. It is designed for storing data and share the data
across containers. Data volume can be provisioned by directly mounting a host
directory, or by a volume plugin that interfaces with a cloud storage backend.

Proposed change
===============
This spec proposes the following changes.

1. Enhance existing API to support bind-mounting Cinder volumes to a container
   as data volumes.

2. Define a pluggable interface that can be implemented by different volume
   drivers. A volume driver is a module that is responsible for managing Cinder
   volumes for containers. Initially, we are going to provide two drivers:
   a Cinder driver and a Fuxi driver.

Cinder driver
=============
This driver is responsible to manage the bind-mounting of Cinder volumes.
If users want to create a container with a volume, they are required to
pre-create the volume in Cinder. Zun will perform the necessary steps to make
the Cinder volume available to the container, which typically includes
retrieving volume information from Cinder, connecting to the volume by using
os-brick library, mounting the connected volume into a directory in the
host's filesystem, and calling Docker API to bind-mount the specific directory
into the container.

The typical workflow to create a container with a Cinder volume will be as
following:

1. A user calls Zun APIs to create a container with a volume::

    $ zun run --volume-driver=cinder -v my-cinder-volume:/data cirros

2. After receiving this request, Zun will make an API call to Cinder to
   reserve the volume. This step will update the status of the volume to
   "attaching" in Cinder to ensure it cannot be used by other users::

    cinderclient.volumes.reserve(volume)

3. Zun makes an API call to Cinder to retrieve the connection information::

    conn_info = cinderclient.volumes.initialize_connection(volume, ...)

4. Zun uses os-brick library with the returned connection to do the connect.
   A successful connection should return the device information that will be
   used for mounting::

    device_info = brick_connector.connect_volume(conn_info)

5. Zun makes an API call to Cinder to finalize the volume connection.
   This will update the status of the volume from "attaching" to "attached"
   in Cinder::

    cinderclient.volumes.attach(volume)

6. Zun mounts the storage device (provided by step 4) into a directory in the
   host's filesystem, and calls Docker API to create a container and use
   that directory as a data volume::

    $ docker run -d -v /opt/stack/data/zun/mnt/<uuid>:/data cirros

The typical workflow to delete a container with a Cinder volume will be as
following:

1. A user calls Zun APIs to delete a container::

    $ zun delete my-container

2. After receiving this request, Zun will make an API call to Cinder to
   begin detaching the volume. This will update the status of the volume to
   "detaching" state::

    cinderclient.volumes.begin_detaching(volume)

3. Zun uses os-brick library to disconnect the volume::

    device_info = brick_connector.disconnect_volume(conn_info)

4. Zun makes an API call to Cinder to terminate the connection::

    conn_info = cinderclient.volumes.terminate_connection(volume, ...)

5. Zun makes an API call to Cinder to finalize the volume disconnection.
   This will update the status of the volume from "detaching" to "available"
   in Cinder::

    cinderclient.volumes.detach(volume)


Fuxi driver
===========
Fuxi is new OpenStack project which aims to integrate Cinder to Docker
volumes. Fuxi can be used as the unified persistence storage provider for
various storage services such as Cinder and Manila.

The implementation of Cinder is enabled using Fuxi driver from Zun. We need
to implement Cinder driver in Zun which manages volumes, let Fuxi control the
mount/unmount volume from Docker container.

There are two approaches Docker provides to add volume to Container.

1. Using Docker run::

    $ docker run -d --volume-driver=fuxi -v my-named-volume:/data --name web_app

2. Create volume first & then add it to Container::

    $ docker volume create --driver fuxi \
                          --name my-named-volume \
                          -o size=1 \
                          -o fstype=ext4 \
                          -o multiattach=true

    $ docker run -d --name web_app -v my-named-volume:/data

I think we can support both.

1. To implement the first approach, we need following changes

- Introduce fields in Container API -  volume-driver, vol-name, vol-size.
- We pass call to Volume Driver to create volume.
- Volume driver connects to Cinder & handles volume creation.
- Once volume is created in Cinder, then we finally go add volume-driver
  as Fuxi & add volume name which created in Cinder.
- Fuxi should be installed in Docker host and configured with Cinder engine.

2. To implement the second approach, we need following changes

- Introduce Volume API in Zun which has fields volume-driver, volume-name,
  volume-size etc.
- Volume API will connect to volume driver which will sit under
  /zun/volume/driver.py.
- Volume Driver connects to Cinder and handles volume creation in Cinder.
- Once the volume is created in Cinder, it communicates to Docker Volume API
  to attach the created volume in Docker.
- Docker Volume API use --driver=Fuxi which goes talks to Cinder and attach
  created Volume in Docker.
- Prerequisite here is, Fuxi should be installed on Docker host & configured
  with Cinder. If not, it returns the 500 response.
- Also we need to introduce new Volume table which contains field vol-driver,
  vol-name, vol-size fields.
- We need to add storage section in conf file, where we can specify some
  default attributes like storage engine Cinder, Cinder endpoint etc.
- We also need to configure Cinder endpoint in Fuxi conf file.
- We can use same implementation for Flocker also as it supports Cinder.
- I think if we can create separate CinderDriver which calls from Volume
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
   to configure volumes of a container should be similar to the VM equivalent.

2. Full-featured container APIs.


Alternatives
------------
1. We can use rexray [2] for storage support, its again third party tool which
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

4. Delete Volume - DELETE /v1/volumes/<uuid>

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

2. Implement volume driver in Zun.

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

References
==========
[1] https://docs.docker.com/engine/tutorials/dockervolumes/

[2] https://github.com/codedellemc/rexray
