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

====================
 Capsule quick start
====================
Capsule is a container composition unit that includes sandbox container,
multiple application containers and multiple volumes. All container inside
the capsule share the same network, ipc, pid namespaces.

The diagram below is an overview of the structure of ``capsule``.

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

Capsule API is currently in experimental phase, so you have to
specify ``--experimental-api`` option in each of the commands below. They will
be moved to stable API once they become stable.

.. note::

   Please make sure that every capsule commands have ``--experimental-api``
   flags in client side.

Experimental API is a separated API. After users deploy Zun by devstack,
a separated set of API endpoints and service type will be created in
service catalog. Zun stable API endpoints will have service name ``zun`` and
service type ``container``, while Zun experimental API endpoints will have
service name ``zun-experimental`` and service type ``container-experimental``.
We can see the service and endpoint information as below::

    +------------------+------------------------+---------+-----------+--------------------------------------+
    | Service Name     | Service Type           | Enabled | Interface | URL                                  |
    +------------------+------------------------+---------+-----------+--------------------------------------+
    | zun              | container              | True    | public    | http://***/container/v1              |
    | zun              | container              | True    | internal  | http://***/container/v1              |
    | zun              | container              | True    | admin     | http://***/container/v1              |
    | zun-experimental | container-experimental | True    | public    | http://***/container/experimental    |
    | zun-experimental | container-experimental | True    | internal  | http://***/container/experimental    |
    | zun-experimental | container-experimental | True    | admin     | http://***/container/experimental    |
    +------------------+------------------------+---------+-----------+--------------------------------------+

Now basic capsule functions are supported. Capsule API methods:

* Create: Create a capsule based on special yaml file or json file.
* Delete: Delete an existing capsule.
* Describe: Get detailed information about selected capsule.
* List: List all the capsules with essential fields.

.. note::

   Volume is not yet supported, but it is in the roadmap. It will be
   implemented after Zun volume support has been finished.

If you need to access to the capsule port, you might need to open the port in
security group rules and access the port via the floating IP that assigned to
the capsule. The capsule example below assumes that a capsule has been launched
with security group "default" and user want to access the port 3306:

.. code-block:: yaml

    capsule_template_version: 2017-06-21
    capsule_version: beta
    kind: capsule
    metadata:
      name: capsule-example
      labels:
        app: web
        nihao: baibai
    restart_policy: always
    spec:
      containers:
      - image: ubuntu
        command:
          - "/bin/bash"
        image_pull_policy: ifnotpresent
        workdir: /root
        labels:
          app: web
        ports:
          - name: nginx-port
            containerPort: 80
            hostPort: 80
            protocol: TCP
        resources:
          allocation:
            cpu: 1
            memory: 1024
        environment:
          PATCH: /usr/local/bin
      - image: centos
        command:
          - "echo"
        args:
          - "Hello"
          - "World"
        image_pull_policy: ifnotpresent
        workdir: /root
        labels:
          app: web01
        ports:
          - name: nginx-port
            containerPort: 80
            hostPort: 80
            protocol: TCP
          - name: mysql-port
            containerPort: 3306
            hostPort: 3306
            protocol: TCP
        resources:
          allocation:
            cpu: 1
            memory: 1024
        environment:
          NWH: /usr/bin/
      volumes:
      - name: volume1
        drivers: cinder
        driverOptions: options
        size: 5GB
        volumeType: type1
        image: ubuntu-xenial

Capsule management commands in details:

Create capsule, it will create capsule based on capsule.yaml:

.. code-block:: console

   $ source ~/devstack/openrc demo demo
   $ zun --experimental-api capsule-create -f capsule.yaml
   $ openstack security group rule create default \
     --protocol tcp --dst-port 3306:3306 --remote-ip 0.0.0.0/0

Delete capsule:

.. code-block:: console

   $ zun --experimental-api capsule-delete <uuid>
   $ zun --experimental-api capsule-delete <capsule-name>

List capsule:

.. code-block:: console

   $ zun --experimental-api capsule-list

Describe capsule:

.. code-block:: console

   $ zun --experimental-api capsule-describe <uuid>
   $ zun --experimental-api capsule-describe <capsule-name>
