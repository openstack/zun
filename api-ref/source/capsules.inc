.. -*- rst -*-

=======================
 Manage Capsules (Pods)
=======================

Lists, creates, shows details for, and deletes capsules.

Capsules is a collection of containers that can run on a host.
It is basically a Zun implementation of Kubernetes Pod.
Containers inside a capsule share the Neutron network and Cinder volumes.

Create new capsule
==================

.. rest_method:: POST /v1/capsules/

Create new capsule.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

Capsule Template
^^^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - template: capsule-template-request
  - kind: capsule-kind-request
  - metadata: capsule-metadata-request
  - metadata.labels: capsule-labels-request
  - metadata.name: capsule-name-request
  - metadata.annotations: capsule-annotations-request
  - spec: capsule-spec-request

.. _create-capsule-spec:

Capsule Spec
^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - containers: capsule-containers-request
  - initContainers: capsule-initContainers-request
  - restartPolicy: capsule-restartPolicy-request
  - volumes: capsule-volumes-request

.. _create-capsule-container:

Capsule Container
^^^^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - image: image
  - command: capsule-command-request
  - args: capsule-args-request
  - env: environment-request
  - name: capsule-container-name-request
  - ports: capsule-ports-request
  - ports.containerPort: capsule-ports-containerPort
  - ports.protocol: capsule-ports-protocol
  - resources: capsule-resources-request
  - resources.cpu: capsule-resources-cpu
  - resources.memory: capsule-resources-memory
  - volumeMounts: capsule-volumeMounts-request
  - volumeMounts.name: capsule-volumeMounts-name
  - volumeMounts.mountPath: capsule-volumeMounts-mountPath
  - workDir: workdir-request

.. _create-capsule-volume:

Capsule Volume
^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - name: capsule-volume-name-request
  - cinder: capsule-cinder-request
  - cinder.volumeID: capsule-cinder-volumeID
  - cinder.size: capsule-cinder-size
  - cinder.autoRemove: capsule-cinder-autoRemove

Request Example
---------------

.. literalinclude:: samples/capsule-create-req.json
   :language: javascript

Response
--------

Capsule
^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: capsule-addresses
  - containers: capsule-containers-create
  - cpu: capsule-cpu
  - memory: capsule-memory
  - uuid: capsule-uuid
  - name: capsule-name
  - labels: capsule-labels
  - annotations: capsule-annotations
  - restart_policy: capsule-restart_policy
  - created_at: created_at
  - updated_at: updated_at
  - user_id: capsule-user_id
  - project_id: capsule-project_id
  - status: capsule-status
  - status_reason: capsule-status_reason
  - links: capsule-links

.. _create-capsule-container-response:

Capsule Container
^^^^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: addresses
  - image: image
  - labels: labels
  - disk: disk
  - security_groups: security_groups
  - task_state: task_state
  - user_id: user_id
  - uuid: container_uuid
  - hostname: hostname
  - environment: environment
  - memory: memory
  - project_id: container-project_id
  - status: status
  - environment: environment
  - workdir: workdir
  - healthcheck: healthcheck
  - auto_remove: auto_remove
  - auto_heal: auto_heal
  - cpu_policy: cpu_policy
  - image_driver: image_driver
  - status_detail: status_detail
  - status_reason: status_reason
  - name: name
  - restart_policy: restart_policy
  - cpu: cpu
  - command: command
  - registry_id: registry_id
  - ports: ports
  - interactive: interactive
  - tty: tty

Response Example
----------------

.. literalinclude:: samples/capsule-create-resp.json
   :language: javascript

List all capsules
=================

.. rest_method:: GET /v1/capsules/

List all available capsules in Zun.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Request
-------

This request does not contain anything in the request body.

Response
--------

Capsule
^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: capsule-addresses
  - containers: capsule-containers-list
  - cpu: capsule-cpu
  - memory: capsule-memory
  - uuid: capsule-uuid
  - name: capsule-name
  - labels: capsule-labels
  - annotations: capsule-annotations
  - restart_policy: capsule-restart_policy
  - created_at: created_at
  - updated_at: updated_at
  - user_id: capsule-user_id
  - project_id: capsule-project_id
  - status: capsule-status
  - status_reason: capsule-status_reason
  - links: capsule-links

.. _list-capsule-container-response:

Capsule Container
^^^^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: addresses
  - image: image
  - labels: labels
  - disk: disk
  - security_groups: security_groups
  - task_state: task_state
  - user_id: user_id
  - uuid: container_uuid
  - hostname: hostname
  - environment: environment
  - memory: memory
  - project_id: container-project_id
  - status: status
  - environment: environment
  - workdir: workdir
  - healthcheck: healthcheck
  - auto_remove: auto_remove
  - auto_heal: auto_heal
  - cpu_policy: cpu_policy
  - image_driver: image_driver
  - status_detail: status_detail
  - status_reason: status_reason
  - name: name
  - restart_policy: restart_policy
  - cpu: cpu
  - command: command
  - registry_id: registry_id
  - ports: ports
  - interactive: interactive
  - tty: tty

Response Example
----------------

.. literalinclude:: samples/capsule-get-all-resp.json
   :language: javascript

Show details of a capsule
=========================

.. rest_method:: GET /v1/capsules/{capsule_ident}

Get all information of a capsule in Zun.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - capsule_ident: capsule_ident

Response
--------

Capsule
^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: capsule-addresses
  - containers: capsule-containers-show
  - cpu: capsule-cpu
  - memory: capsule-memory
  - uuid: capsule-uuid
  - name: capsule-name
  - labels: capsule-labels
  - annotations: capsule-annotations
  - restart_policy: capsule-restart_policy
  - created_at: created_at
  - updated_at: updated_at
  - user_id: capsule-user_id
  - project_id: capsule-project_id
  - status: capsule-status
  - status_reason: capsule-status_reason
  - links: capsule-links

.. _show-capsule-container-response:

Capsule Container
^^^^^^^^^^^^^^^^^

.. rest_parameters:: parameters.yaml

  - addresses: addresses
  - image: image
  - labels: labels
  - disk: disk
  - security_groups: security_groups
  - task_state: task_state
  - user_id: user_id
  - uuid: container_uuid
  - hostname: hostname
  - environment: environment
  - memory: memory
  - project_id: container-project_id
  - status: status
  - environment: environment
  - workdir: workdir
  - healthcheck: healthcheck
  - auto_remove: auto_remove
  - auto_heal: auto_heal
  - cpu_policy: cpu_policy
  - image_driver: image_driver
  - status_detail: status_detail
  - status_reason: status_reason
  - name: name
  - restart_policy: restart_policy
  - cpu: cpu
  - command: command
  - registry_id: registry_id
  - ports: ports
  - interactive: interactive
  - tty: tty

Response Example
----------------

.. literalinclude:: samples/capsule-show-resp.json
   :language: javascript

Delete a capsule
================

.. rest_method:: DELETE /v1/capsules/{capsule_ident}

Delete a capsule.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - capsule_ident: capsule_ident

Response
--------

This request does not return anything in the response body.
