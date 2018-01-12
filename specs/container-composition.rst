..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================
Container Composition
=====================
Related Launchpad Blueprint:

https://blueprints.launchpad.net/zun/+spec/introduce-compose

Kubernetes Pod[1] or Docker compose[2] are popular for deploying applications
or application components that span multiple containers. It is a basic unit for
scheduler, resource allocation. This spec proposes to support a similar
feature in Zun, we can put multiple containers, a sandbox and other related
resources into one unit, we name the unit ``capsule``.

The containers in a ``capsule`` are relatively tightly coupled, they share
the capsule's context like Linux namespaces, cgroups and etc, and they work
together closely to form a cohesive unit of service.


Problem description
===================
Currently running or deploying one container to do the operation is not a
very effective way in micro services, while multiple different containers run
as an integration has widely used in different scenarios, such as pod in
Kubernetes. The pod has the independent network, storage, while the compose has
an easy way to defining and running multi-container Docker applications. They
are becoming the basic unit for container application scenarios.

Nowadays Zun doesn't support creating and running multiple containers as an
integration. So we will introduce the new Object ``capsule`` to realize this
function. ``capsule`` is the basic unit for zun to support service to external.

The ``capsule`` will be designed based on some similar concepts such as pod and
compose. For example, ``capsule`` can be specified in a yaml file that might be
similar to the format of k8s pod manifest. However, the specification of
``capsule`` will be exclusive to Zun. The details will be showed in the
following section.

Proposed change
===============
A ``capsule`` has the following properties:
* Structure: It can contains one or multiple containers, and has a sandbox
container which will support the network namespace for the capsule.
* Scheduler: Containers inside a capsule are scheduled as a unit, thus all
containers inside a capsule is co-located. All containers inside a capsule
will be launched in one compute host.
* Network: Containers inside a capsule share the same network namespace, so
they share IP address(es) and can find each other via localhost by using
different remapping network port. Capsule IP address(es) will re-use the
sandbox IP. Containers communication between different capsules will use
capsules IP and port.
* LifeCycle: Capsule has different status:
Starting: Capsule is created, but one or more container inside the capsule is
being created.
Running: Capsule is created, and all the containers are running.
Finished: All containers inside the capsule have successfully executed
and exited.
Failed: Capsule creation is failed
* Restart Policy: Capsule will have a restart policy just like container.
The restart policy relies on container restart policy to execute.
* Health checker:
In the first step of realization, container inside the capsule will send its
status to capsule when its status changed.
* Upgrade and rollback:
Upgrade: Support capsule update(different from zun update). That means the
container image will update, launch the new capsule from new image, then
destroy the old capsule. The capsule IP address will change. For Volume,
need to clarify it after Cinder integration.
Rollback: When update failed, rollback to it origin status.
* CPU and memory resources: Given that host resource allocation, cpu and memory
support will be implemented.

Implementation:

1. Introduce a new abstraction called ``capsule``. It represents a tightly
   coupled unit of multiple containers and other resources like sandbox. The
   containers in a capsule shares the capsule's context like Linux namespaces
   and cgroups.
2. Support the CRUD operations against capsule object, capsule should be a
   basic unit for scheduling and spawning. To be more specific, all containers
   in a capsule should be scheduled to and spawned on the same host. Server
   side will keep the information in DB.
3. Add functions about yaml file parser in the CLI side. After parsing the
   yaml, send the REST to API server side, scheduler will decide which host to
   run the capsule.
4. Introduce new REST API for capsule. The capsule creation workflow is:
   CLI Parsing capsule information from yaml file -->
   API server do the CRUD operation, call scheduler to launch the capsule,
   from Cinder to get volume, from Kuryr to get network support -->
   Compute host launch the capsule, attach the volume -->
   Send the status to API server, update the DB.
5. Capsule creation will finally depend on the backend container driver.
   Now choose Docker driver first.
6. Define a yaml file structure for capsule. The yaml file will be compatible
   with Kubernetes pod yaml file, at the same time Zun will define the
   available properties, metadata and template of the yaml file. In the first
   step, only essential properties will be defined.

The diagram below offers an overview of the architecture of ``capsule``.

::

    +-----------------------------------------------------------+
    |                       +-----------+                       |
    |                       |           |                       |
    |                       |  Sandbox  |                       |
    |                       |           |                       |
    |                       +-----------+                       |
    |                                                           |
    |                                                           |
    |   +-------------+    +-------------+    +-------------+   |
    |   |             |    |             |    |             |   |
    |   |  Container  |    |  Container  |    |  Container  |   |
    |   |             |    |             |    |             |   |
    |   +-------------+    +-------------+    +-------------+   |
    |                                                           |
    |                                                           |
    |              +----------+       +----------+              |
    |              |          |       |          |              |
    |              |  Volume  |       |  Volume  |              |
    |              |          |       |          |              |
    |              +----------+       +----------+              |
    |                                                           |
    +-----------------------------------------------------------+

Yaml format for ``capsule``:

Sample capsule:

.. code-block:: yaml

    apiVersion: beta
    kind: capsule
    metadata:
      name: capsule-example
      lables:
        app: web
    restartPolicy: Always
    hostSelector: node1
    spec:
      containers:
      - image: ubuntu:trusty
        command: ["echo"]
        args: ["Hello World"]
        imagePullPolicy: Always
        imageDriver: Glance
        workDir: /root
        labels:
          app: web
        volumeMounts:
          - name: volume1
            mountPath: /root/mnt
            readOnly: True
        ports:
          - name: nginx-port
            containerPort: 80
            hostPort: 80
            protocol: TCP
        env:
          PATH: /usr/local/bin
        resources:
          requests:
            cpu: 1
            memory: 2GB
      volumes:
        - name: volume1
        drivers: cinder
        driverOptions: options
        size: 5GB
        volumeType: type1
        image: ubuntu-xenial

Capsule fields:
* apiVersion(string): the first version is beta
* kind(string): the flag to show yaml file property
* metadata(ObjectMeta): metadata Object
* spec(CapsuleSpec): capsule specifications
* restartPolicy(string): [Always | Never | OnFailure], by default is Always
* hostSelector(string): Specify the host that will launch the capsule

ObjectMeta fields:
* name(string): capsule name
* lables(dict, name: string): labels for capsule

CapsuleSpec fields:
* containers(Containers array): containers info array, one capsule have
multiple containers
* volumes(Volumes array): volume information

Containers fields:
* name(string): name for container
* image(string): container image for container
* imagePullPolicy(string): [Always | Never | IfNotPresent]
* imageDriver(string): glance or dockerRegistory, by default is according to
zun configuration
* command(string): container command when starting
* args(string): container args for the command
* workDir(string): workDir for the container
* labels(dict, name:string): labels for the container
* volumeMounts(VolumnMounts array): volumeMounts information for container
* ports(Ports array): Port mapping information for container
* env(dict, name:string): environment variables for container
* resources(RecourcesObject): resources that container needed

VolumnMounts fields:
* name(string): volume name that listed in below field "volumes"
* mountPath(string): mount path that in the container, absolute path
* readOnly(boolean): read only flags

Ports fields:
* name(string): port name, optional
* containerPort(int): port number that container need to listen
* hostPort(int): port number that capsule need to listen
* protocol(string): TCP or UDP, by default is TCP

RecourcesObject fields:
* requests(AllocationObject): the resources that the capsule needed

AllocationObject:
* cpu(string): cpu resources, cores number
* memory(string): memory resources, MB or GB

Volumes fields:
* name(string): volume name
* driver(string): volume drivers
* driverOptions(string): options for volume driver
* size(string): volume size
* volumeType(string): volume type that cinder need. by default is from cinder
config
* image(string): cinder needed to boot from image

Alternatives
------------
1. Abstract all the information from yaml file and implement the capsule CRUD
   in client side.
2. Implement the CRUD in server side.


Data model impact
-----------------
* Add a field to container to store the id of the capsule which include the
  container
* Create a 'capsule' table. Each entry in this table is a record of a capsule.

.. code-block:: python

    Introduce the capsule Object:
        fields = {
        'capsuleVersion': fields.StringField(nullable=True),
        'kind': fields.StringField(nullable=True),
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),

        'status': z_fields.ContainerStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),

        # conclude the readable message that show why capsule is in this status
        # 'key': 'value'--> 'time':'message'
        'message': fields.DictOfStringsField(nullable=True),
        'startTime': fields.StringField(nullable=True),

        'cpu': fields.FloatField(nullable=True),
        'memory': fields.StringField(nullable=True),
        'task_state': z_fields.TaskStateField(nullable=True),
        'host': fields.StringField(nullable=True),
        'restart_policy': fields.DictOfStringsField(nullable=True),

        'meta': fields.DictOfStringsField(nullable=True),
        'volumes': fields.DictOfStringsField(nullable=True),
        'ip': fields.StringField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'ports': z_fields.ListOfIntegersField(nullable=True),
        'hostname': fields.StringField(nullable=True),
    }

REST API impact
---------------
* Add a new API endpoint /capsule to the REST API interface.
* Capsule API: Capsule consider to support multiple operations as container
  composition.
* Container API: Many container API will be extended to capsule. Here in this
  section will define the API usage range.

::

  Capsule API:
  list              <List all the capsule, add parameters about list capsules with the same labels>
  create            <-f yaml file><-f directory>
  describe          <display the details state of one or more resource>
  delete
                    <capsule name>
                    <-l name=label-name>
                    <–all>
  run               <--capsule ... container-image>
                    If "--capsule .." is set, the container will be created inside the capsule.
                    Otherwise, it will be created as normal.

  Container API:
  * show/list               allow all containers
  * create/delete           allow bare container only (disallow in-capsule containers)
  * attach/cp/logs/top      allow all containers
  * start/stop/restart/kill/pause/unpause  allow bare container only (disallow in-capsule containers)
  * update                  for container in the capsule, need <--capsule> params.
                            Bare container doesn't need.

Security impact
---------------
None


Notifications impact
--------------------
Need to support "zun notification" for capsule events


Other end user impact
---------------------
None


Performance Impact
------------------
None


Other deployer impact
---------------------
None


Developer impact
----------------
None


Implementation
==============
The implementation is divided into the following parts:
1. Define the ``capsule`` data structure. Take Kubernetes Pod as a
reference.
2. Define the yaml structure for ``capsule``, add the parser for the
yaml file. The parser realization is in CLI. CLI parse info from yaml
and then send to API server.
3. Implement a new API endpoint for capsule, including capsule life
cycle and information.
4. Implement the API server side, including DB CRUD, compute node
scheduler, etc.
5. Implement the compute server side, now using Docker Driver first.
The first step will just realize the several containers in the same
sandbox which have the same network namespace. The storage share in
the capsule will be added after Cinder integration.

We will split the implementation into several blueprints for easy task
tracking.

Assignee(s)
-----------

Primary assignee:
Wenzhi Yu <yuywz>
Kevin Zhao <kevinz>


Work Items
----------
1. Implement a new API endpoint for capsules.
2. Implement unit/integration test.
3. Document the new capsule API.


Dependencies
============
1. Need to add support for select host to launch capsule
2. Need to add support for port mapping
3. Need to support "zun notification" for capsule events

Testing
=======
Each patch will have unit tests, and Tempest functional tests covered.


Documentation Impact
====================
A set of documentation for this new feature will be required.


References
==========
[1] https://kubernetes.io/

[2] https://docs.docker.com/compose/

[3] https://etherpad.openstack.org/p/zun-container-composition
