..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

==================
Container Snapshot
==================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/container-snapshot
Zun needs to snapshot a running container, and make it available to user.
Potentially, a user can restore the container from this snapshot image.

Problem description
===================
It is a common requirement from users of containers to save the changes of a
current running container to a new image. Zun currently does not support
taking a snapshot of a container.

Proposed change
===============
1. Introduce a new CLI command to enable a user to take a snapshot of a running
   container instance::

    $ zun commit <container-name> <image-name>

    $ zun help commit

    usage: zun commit <container-name> <image-name>
            Create a new image by taking a snapshot of a running container.
    Positional arguments:
            <container-name>              Name or ID of container.
            <image-name>                  Name of snapshot.

2. Extend docker driver to enable "docker commit" command to create a
   new image.

3. The new image should be accessible from other hosts. There are two
   options to support this:
   a) upload the image to glance
   b) upload the image to docker hub
   Option a) will be implemented as default; future enhancement can be
   done to support option b).

Design Principles
=================
Similar user experience between VMs and containers. In particular,
the ways to snapshot a container should be similar as the VM equivalent.

Alternatives
============
1. Using linked volumes to persistent changes in a container.
2. Use docker cp to copy data from the container onto the host machine.

Data model impact
=================
None

REST API impact
===============
Creates an image from a container.

Specify the image name in the request body.

After making this request, a user typically must keep polling the status of the
created image from glance to determine whether the request succeeded.
If the operation succeeds, the created image has a status of active. User can
also see the new image in the image back end that OpenStack Image service
manages.

Preconditions:

1. The container must exist.

2. User can only create a new image from the container when its status is
   Running, Stopped, and Paused.

3. The connection to the Image service is valid.

::

    POST /containers/<ID>/commit:        commit a container
    Example commit
    {
        "image-name" : "foo-image"
    }

Response:
If successful, this method does not return content in the response body.
- Normal response codes: 202
- Error response codes: BadRequest(400), Unauthorized(401), Forbidden(403),
ItemNotFound(404)

Security impact
===============
None

Notifications impact
====================
None

Other end user impact
=====================
None

Performance Impact
==================
None

Other deployer impact
=====================
None

Developer impact
================
None

Implementation
==============
Assignee(s)
Primary assignee: Bin Zhou
Other contributors:
Work Items
1. Expend docker driver to enable "docker commit".
2. Upload the generated image to glance.
3. Implement a new API endpoint for createImage.
4. Implement unit/integration test.

Dependencies
============
None

Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.

Documentation Impact
====================
A set of documentation for this new feature will be required.
