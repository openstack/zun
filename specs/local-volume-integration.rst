..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

============================
Local Volume Integration
============================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/support-volume-binds

Zun has introduced an option for users to bind-mount Cinder volumes
to containers.
However, users can't bind-mount file or directory in local file system
into the container. This function is like the option '-v' of docker run/create:
$ docker run -v /host/path:/container/path <image>
The above command will bind-mount the directory with path '/host/path'
into path '/container/path' inside the container.

Problem description
===================
Some special application containers need use the files/directories
in localhost for initializing process or getting a large amount of data.
So zun should implement the option, and this option should work well with
the cinder volume together.

Proposed change
===============
This spec proposes the following changes.

1. It's unsafe to mount the host directory into the container, so only admin
   can bind-mount file or directory in local file system into the container.

2. We leverage the --mount option for cinder volume bindmount. It is better to
   reuse this option for bind-mounting local file system.
   For example:
   $ zun run --mount type=<local|cinder>,source=...,destination=... <image>

3. Zun introduces a config (called 'allowed_mount_path.conf').
   Operators can tune this config to restrict the path for bind-mounting.

4. The administrator would be aware that a special container should be
   scheduled on which nodes. Users may combine --mount and --hint options to
   create a container.

Workflow
=============
The typical workflow to create a container with a Local volume will be as
following:

1. A user calls Zun APIs to create a container with a local volume::

    $ zun run --mount type=local,source=/proc,destination=/proc \
      --hint <key=value> centos

2. After receiving this request, Zun will check if the mount info has local
   volumes. Then it will check the user has administrator permissions
   operation.

3. Zun will create an item for local volume, and store in the volume_mapping
   table.

4. Zun will choose a node by the option --hint, and check the local volume
   whether in the volume lists in forbidden_volume.conf.

5. Zun will calls Docker API to create a container and use the option "-v".

    $ docker run -d -v /proc:/proc centos

Security impact
---------------
1. Only admin can bind-mount file or directory in local file system into the
   container.

2. Zun introduces a config (called 'allowed_mount_path.conf') to check the
   files/directories can be bind-mounted. When the config is unsetted or empty,
   zun will raise Exception when using the bind-mounted option.


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
Deployers need to deploy a Cinder.


Developer impact
----------------
None


Implementation
==============


Assignee(s)
-----------
Primary assignee:
Feng Shengqin

Other contributors:


Dependencies
============


Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.

References
==========
[1] https://docker-py.readthedocs.io/en/stable/containers.html#container-objects.

