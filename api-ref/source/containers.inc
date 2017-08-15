.. -*- rst -*-

===================
 Manage Containers
===================

Lists, creates, shows details for, stats, updates, deletes, starts,
stops, pauses, unpauses, restarts, renames, commits containers, and adds
security group for specified container.

Create new container
====================

.. rest_method:: POST /v1/containers/

Create new container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - name: name
  - image: image
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - labels: labels
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - image_driver: image_driver
  - security_groups: security_groups
  - nets: nets
  - runtime: runtime

Request Example
----------------

.. literalinclude:: samples/container-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - links: links
  - addresses: addresses
  - name: name
  - image: image
  - labels: labels
  - image_driver: image_driver
  - security_groups: security_groups
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports

Response Example
----------------

.. literalinclude:: samples/container-create-resp.json
   :language: javascript

List all containers
===================

.. rest_method:: GET /v1/containers/

List all available containers in Zun.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Response
--------

.. rest_parameters:: parameters.yaml

  - containers: container_list
  - links: links
  - addresses: addresses
  - name: name
  - image: image
  - labels: labels
  - image_driver: image_driver
  - security_groups: security_groups
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports

Response Example
----------------

.. literalinclude:: samples/container-get-all-resp.json
   :language: javascript

Show details of a container
===========================

.. rest_method:: GET /v1/containers/{container_ident}

Get all information of a container in Zun.

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

  - container_ident: container_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - links: links
  - addresses: addresses
  - name: name
  - image: image
  - labels: labels
  - image_driver: image_driver
  - security_groups: security_groups
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports

Response Example
----------------

.. literalinclude:: samples/container-show-resp.json
   :language: javascript

Delete a container
==================

.. rest_method:: DELETE /v1/containers/{container_ident}

Delete a container. To delete a container in `Creating` or `Running`
state, request to /v1/containers/{container_ident}?force=True

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

  - container_ident: container_ident
  - force: force

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Display stats of a container
============================

.. rest_method:: GET /v1/containers/{container_ident}/stats

Display stats of a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident

Response
--------

.. rest_parameters:: parameters.yaml

  - stats_info: stats_info

Response Example
----------------

.. literalinclude:: samples/container-stats-resp.json
   :language: javascript


Update information of container
===============================

.. rest_method:: PATCH /v1/containers/{container_ident}

Update information of one container attributes. Currently only `cpu` and
`memory` can be updated.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - memory: memory
  - cpu: cpu

Request Example
----------------

.. literalinclude:: samples/container-update-req.json
   :language: javascript

Response
--------

Return new container with updated attributes.

.. rest_parameters:: parameters.yaml

  - links: links
  - addresses: addresses
  - name: name
  - image: image
  - labels: labels
  - image_driver: image_driver
  - security_groups: security_groups
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports

Response Example
----------------

.. literalinclude:: samples/container-update-resp.json
   :language: javascript

Start a container
=================

.. rest_method:: POST /v1/containers/{container_ident}/start

Start a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Stop a container
================

.. rest_method:: POST /v1/containers/{container_ident}/stop?timeout={timeout}

Stop a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - timeout: timeout

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Pause a container
=================

.. rest_method:: POST /v1/containers/{container_ident}/pause

Pause a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Unpause a container
===================

.. rest_method:: POST /v1/containers/{container_ident}/unpause

Unpause a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id

Restart a container
===================

.. rest_method:: POST /v1/containers/{container_ident}/reboot?timeout={timeout}

Restart a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - timeout: timeout

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Rename a container
==================

.. rest_method:: POST /v1/containers/{container_ident}/rename?name={new_name}

Rename a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - new_name: new_name

Response
--------

.. rest_parameters:: parameters.yaml

  - links: links
  - addresses: addresses
  - name: name
  - image: image
  - labels: labels
  - image_driver: image_driver
  - security_groups: security_groups
  - command: command
  - cpu: cpu
  - memory: memory
  - workdir: workdir
  - image_pull_policy: image_pull_policy
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports

Response Example
----------------

.. literalinclude:: samples/container-rename-resp.json
   :language: javascript


Add security group for specified container
==========================================

.. rest_method:: POST /v1/containers/{container_ident}/add_securtiy_group?name=security_group

Add security group for specified container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - security_group: security_groups

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Commit a container
==================

.. rest_method:: POST /v1/containers/{container_ident}/commit?tag={tag}&repository={repository}

Create a new image from a container's changes

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - repository: repository
  - tag: tag

Response
--------

.. rest_parameters:: parameters.yaml

  - image: image


Detach a network from a container
================================

.. rest_method:: POST /v1/containers/{container_ident}/network_detach?network={network}

Detach a network from a container.

Response Codes
-------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

.. rest_parameters:: parameters.yaml

   - container_ident: container_ident
   - network: network

Response
--------

This request does not return anything in the response body.

.. rest_parameters:; parameters.yaml
   - X-Openstack-Request-Id: request_id
