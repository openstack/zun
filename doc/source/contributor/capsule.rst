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
 Capsule Quick Start
====================
Capsule is a container composition unit that includes sandbox container,
multiple application containers and multiple volumes. All container inside
the capsule share the same network, ipc, pid namespaces. In general, it is
the same unit like Azure Container Instance(ACI) or Kubernetes Pod.

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

Capsule API is currently in v1 phase now.

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
with security group "default" and user want to access the port 22, 80 and 3306:

.. code-block:: yaml

    # use "-" because that the fields have many items
    capsuleVersion: beta
    kind: capsule
    metadata:
      name: template
      labels:
        app: web
        foo: bar
    restartPolicy: Always
    spec:
      containers:
      - image: ubuntu
        command:
          - "/bin/bash"
        imagePullPolicy: ifnotpresent
        workDir: /root
        ports:
          - name: ssh-port
            containerPort: 22
            hostPort: 22
            protocol: TCP
        resources:
          requests:
            cpu: 1
            memory: 1024
        env:
          ENV1: /usr/local/bin
          ENV2: /usr/sbin
        volumeMounts:
        - name: volume1
          mountPath: /data1
          readOnly: True
      - image: centos
        command:
          - "/bin/bash"
        args:
          - "-c"
          - "\"while true; do echo hello world; sleep 1; done\""
        imagePullPolicy: ifnotpresent
        workDir: /root
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
          requests:
            cpu: 1
            memory: 1024
        env:
          ENV2: /usr/bin/
        volumeMounts:
        - name: volume2
          mountPath: /data2
        - name: volume3
          mountPath: /data3
      volumes:
      - name: volume1
        cinder:
          size: 5
          autoRemove: True
      - name: volume2
        cinder:
          volumeID: 9f81cbb2-10f9-4bab-938d-92fe33c57a24
      - name: volume3
        cinder:
          volumeID: 67618d54-dd55-4f7e-91b3-39ffb3ba7f5f

Pay attention, the volume2 and volume3 referred in the above yaml are already
created by Cinder. Also capsule doesn't support Cinder multiple attach now.
One volume only could be attached to one Container.

Capsule management commands in details:

Create capsule, it will create capsule based on capsule.yaml:

.. code-block:: console

   $ source ~/devstack/openrc demo demo
   $ zun capsule-create -f capsule.yaml

If you want to get access to the port, you need to set the security group
rules for it.

.. code-block:: console

   $ openstack security group rule create default \
     --protocol tcp --dst-port 3306:3306 --remote-ip 0.0.0.0/0
   $ openstack security group rule create default \
     --protocol tcp --dst-port 80:80 --remote-ip 0.0.0.0/0
   $ openstack security group rule create default \
     --protocol tcp --dst-port 22:22 --remote-ip 0.0.0.0/0

Delete capsule:

.. code-block:: console

   $ zun capsule-delete <uuid>
   $ zun capsule-delete <capsule-name>

List capsule:

.. code-block:: console

   $ zun capsule-list

Describe capsule:

.. code-block:: console

   $ zun capsule-describe <uuid>
   $ zun capsule-describe <capsule-name>

TODO
---------

`Add security group set to Capsule`
    Build this documentation and push it to .

`Add Gophercloud support for Capsule`
    See `Gophercloud support for Zun
    <https://blueprints.launchpad.net/zun/+spec/golang-client>`_

`Add Kubernetes connect to Capsule`
    see `zun connector for k8s
    <https://blueprints.launchpad.net/zun/+spec/zun-connector-for-k8s>`_.

