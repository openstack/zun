..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

==========================
Container Interactive mode
==========================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/support-interactive-mode

Zun needs to support the function that the interactive mode which is the
basic function in Docker and rkt. Currently user can run commands inside a
container using zun. With interactive mode, users will be able to perform
interactive operations on these containers using Zun APIs.

The implementation of interactive mode is driver-specific. Each driver needs to
implement this function needs to do different thing about API command and
interactive interface. Take docker driver as the first container driver.

Problem description
===================
Zun containers now take Docker as the first container driver. Docker can use
"docker run -it" to enter into the interactive mode, where user can do
operations looks like chroot. Zun use docker-py as the interface to get access
the docker deamon.

To reach the goal of realizing the container interactive, zun needs to pass the
correct parameters when create container and start container at the time
it has been created, so that a tty will be created inside the container. User
can connect the stdin, stdout, stderr to get a pseudo tty in local client.
Since Kubernetes realize this function, refer to Kubernetes realization is a
feasible way.

https://github.com/kubernetes/kubernetes/pull/3763

For Kubectl interactive description, go to:
https://kubernetes.io/docs/user-guide/kubectl/kubectl_run/

Proposed change
===============
1. Let each Docker daemon listens to 0.0.0.0:port, so that zun-api will easily
   talk with Docker deamon. This might reduce the load on zun-compute a bit
   and let zun-compute have more rooms to serve other workload.
2. For docker daemon, the new two parameters about tty and stdin_open should
   be added to the container field and corresponding database.
3. Zun api will wait for the container start and get the websocket link to zun
   CLIs.
4. For python-zunclient, it will filter the parameters and pick up the correct
   for interactive mode. Then will open the connection to container at local
   terminal after the "zun run" command return. Zun CLIs will directly connect
   the websocket link from Docker daemon (for authorization problem, will fix
   it in the follow bp/bug).

The diagram below offers an overview of the interactive mode architecture.
E.g : zun run -i --name test cirros /bin/sh

The sequence diagram is in this link:
https://github.com/kevin-zhaoshuai/workflow

Design Principles
-----------------
1. Keep commonality for Docker and other container driver. Easy for other
   driver integration.
2. Take into account all the interactive conditions.
3. Pty connection functions need to be independent and extensible


Alternatives
------------

Data model impact
-----------------
Add some fields to container object, including "tty" "stdin_open" and a flag
to show whether the container has been attached,
maybe "attached" = "true"/"false".

REST API impact
---------------
Add an new API for "zun attach"
Zun CLIs will first send the message to zun-api, zun-api will directly talk
with Docker daemon. Then after the container is successfully started, zun-api
notify zun CLIs with the attach url. Zun CLIs will attach its stdin ,stdout
and stderr to the container. Since zun CLIs connect with the websocket in
Docker daemon, so that will not hijack HTTP request (from zun CLIs to zun api),
user can do another zun api command in another terminal.

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


Other deployer impact
---------------------


Developer impact
----------------
In the future integration with other container driver, need to tweak some code
about client pty connection.


Implementation
==============


Assignee(s)
-----------

Primary assignee:
Kevin Zhao

Other contributors:


Work Items
----------
1. Implement a function for connect the tty inside the container.
2. Modify the zun run and zun exec code about the interactive.
3. Implement unit/integration test.

Dependencies
============

Testing
=======
Each patch will have unit tests.


Documentation Impact
====================
A set of documentation for this new feature will be required.
