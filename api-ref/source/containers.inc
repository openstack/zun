.. -*- rst -*-

===================
 Manage Containers
===================

Lists, creates, shows details for, stats, updates, deletes, starts, resizes,
stops, pauses, unpauses, restarts, renames, commits, kills, attaches to containers,
gets archive from container, puts archive to container, and adds security group
for specified container, executes command in a running container, gets logs
of a container, displays the running processes in a container, resizes
the tty session used by the exec, list actions and action detail for a container.

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

  - name: name-request
  - image: image
  - command: command-request
  - cpu: cpu-request
  - memory: memory-request
  - workdir: workdir-request
  - labels: labels-request
  - environment: environment-request
  - restart_policy: restart_policy-request
  - interactive: interactive-request
  - tty: tty-request
  - image_driver: image_driver-request
  - security_groups: security_groups-request
  - nets: nets
  - runtime: runtime
  - hostname: hostname-request
  - auto_remove: auto_remove-request
  - auto_heal: auto_heal-request
  - availability_zone: container_availability_zone
  - hints: hints
  - mounts: mounts
  - privileged: privileged-request
  - healthcheck: healthcheck-request
  - exposed_ports: exposed_ports
  - host: requested_host
  - entrypoint: entrypoint-request

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
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - tty: tty
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports
  - auto_remove: auto_remove
  - auto_heal: auto_heal
  - privileged: privileged
  - healthcheck: healthcheck
  - user_id: user_id
  - project_id: project_id
  - disk: disk
  - registry_id: registry_id
  - cpu_policy: cpu_policy
  - entrypoint: entrypoint


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

Request
-------

.. rest_parameters:: parameters.yaml

  - name: name_query
  - image: image_query
  - project_id: project_id_query
  - user_id: user_id_query
  - memory: memory_query
  - host: host_query
  - task_state: task_state_query
  - status: status_query
  - auto_remove: auto_remove_query

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
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - tty: tty
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports
  - privileged: privileged
  - healthcheck: healthcheck
  - user_id: user_id
  - project_id: project_id
  - disk: disk
  - registry_id: registry_id
  - cpu_policy: cpu_policy
  - entrypoint: entrypoint

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
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - tty: tty
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports
  - privileged: privileged
  - healthcheck: healthcheck
  - user_id: user_id
  - project_id: project_id
  - disk: disk
  - registry_id: registry_id
  - cpu_policy: cpu_policy
  - entrypoint: entrypoint

Response Example
----------------

.. literalinclude:: samples/container-show-resp.json
   :language: javascript

Delete a container
==================

.. rest_method:: DELETE /v1/containers/{container_ident}

Delete a container. To delete a container in `Creating` or `Running`
state, request to /v1/containers/{container_ident}?force=True
To stop and delete a container, request to /v1/containers/{container
_ident}?stop=True

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
  - stop: stop

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Kill a container
================

.. rest_method:: POST /v1/containers/{container_ident}/kill

Kill a running container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409

Request
-------

.. rest_parameters:: parameters.yaml

  - container_ident: container_ident
  - signal: signal

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

Update information of one container attributes. Currently only `cpu`, name and
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
  - name: name

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
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - tty: tty
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports
  - privileged: privileged
  - healthcheck: healthcheck
  - user_id: user_id
  - project_id: project_id
  - disk: disk
  - registry_id: registry_id
  - cpu_policy: cpu_policy
  - entrypoint: entrypoint

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

.. rest_method:: POST /v1/containers/{container_ident}/stop

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

Rebuild a container
===================

.. rest_method:: POST /v1/containers/{container_ident}/rebuild

Rebuild a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - container_ident: container_ident
   - image: image
   - image_driver: image_driver

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id



Restart a container
===================

.. rest_method:: POST /v1/containers/{container_ident}/reboot

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

.. rest_method:: POST /v1/containers/{container_ident}/rename

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
  - environment: environment
  - restart_policy: restart_policy
  - interactive: interactive
  - tty: tty
  - uuid: uuid
  - hostname: hostname
  - status: status
  - status_detail: status_detail
  - host: host
  - task_state: task_state
  - status_reason: status_reason
  - ports: ports
  - user_id: user_id
  - project_id: project_id
  - disk: disk
  - registry_id: registry_id
  - cpu_policy: cpu_policy
  - entrypoint: entrypoint

Response Example
----------------

.. literalinclude:: samples/container-rename-resp.json
   :language: javascript


Get archive from  a container
=============================

.. rest_method:: GET /v1/containers/{container_ident}/get_archive

Get a tar archive of a resource in the filesystem of a container.

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
  - source_path: source_path

Response
--------

.. rest_parameters:: parameters.yaml

  - data: data
  - stat: stat

Response Example
----------------

.. literalinclude:: samples/container-get-archive-resp.json
   :language: javascript

Put archive to a container
==========================

.. rest_method:: POST /v1/containers/{container_ident}/put_archive

Upload a tar archive to be extracted to a path in the filesystem of container.

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
  - destination_path: destination_path
  - data: data

Request Example
----------------

.. literalinclude:: samples/container-put-archive-req.json
   :language: javascript

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Add security group for specified container
==========================================

.. rest_method:: POST /v1/containers/{container_ident}/add_securtiy_group

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
  - security_group: security_group_query

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Commit a container
==================

.. rest_method:: POST /v1/containers/{container_ident}/commit

Create a new image from a container's changes.

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

Response Example
----------------

.. literalinclude:: samples/container-commit-resp.json
   :language: javascript


Attach to a container
=====================

.. rest_method:: GET /v1/containers/{container_ident}/attach

Attach to a running container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
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

This request returns websocket url as a response, which is
not in json format.


Detach a network from a container
=================================

.. rest_method:: POST /v1/containers/{container_ident}/network_detach

Detach a network from a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - container_ident: container_ident
   - network: network-query
   - port: port-query

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Resize a container
==================

.. rest_method:: POST /v1/containers/{container_ident}/resize

Resize tty to a container

.. warning::
   This API is primarily designed to be used by zunclient or Zun-UI.
   The point of this API is to coordinate between client-side tools and
   Zun to adjust the size of the TTY for the container.
   Unless you are writing client-side tools you **should not** be using
   this API.

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
  - width: width
  - height: height

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Attach a network to a container
===============================

.. rest_method:: POST /v1/containers/{container_ident}/network_attach

Attach a network to a container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - container_ident: container_ident
   - network: network-query
   - port: port-query
   - fixed_ip: fixed_ip-query

Response
--------

This request does not return anything in the response body.

.. rest_parameters:: parameters.yaml

  - X-Openstack-Request-Id: request_id


Execute command in a running container
======================================

.. rest_method:: POST /v1/containers/{container_ident}/execute

Execute command in a running container.

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
   - command: exec_command
   - run: exec_run
   - interactive: exec_interactive

Response
--------

.. rest_parameters:: parameters.yaml

  - output: exec_output
  - exit_code: exec_exit_code
  - exec_id: exec_id
  - url: exec_url

.. note::

   If the run parameter is set to true, the output will be
   {"output": "...", "exit_code": "...", "exec_id": None, "url": None}.
   Otherwise, the output will be
   {"output": None, "exit_code": None, "exec_id": "...", "url": "..."}.

Response Example
----------------

.. literalinclude:: samples/container-execute-resp.json
   :language: javascript

.. literalinclude:: samples/container-execute-resp-2.json
   :language: javascript


Resize tty when execute command in a container
==============================================

.. rest_method:: POST /v1/containers/{container_ident}/execute_resize

Resize tty when execute command in a container.

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
   - height: height
   - exec_id: exec_resize_id
   - width: width

Response
--------

.. rest_parameters:: parameters.yaml

  - exec_resize_output: exec_resize_output

Response Example
----------------

.. literalinclude:: samples/container-execute-resize-resp.json
   :language: javascript


Get logs of a container
=======================

.. rest_method:: GET /v1/containers/{container_ident}/logs

Get logs of a container.

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
   - timestamps: timestamps
   - tail: tail
   - stderr: stderr
   - stdout: stdout
   - since: since

Request Example
----------------

.. literalinclude:: samples/container-logs-req.json
   :language: javascript

Response
--------

This request returns logs string as a response, which is
not in json format.


Display the running processes in a container
============================================

.. rest_method:: GET /v1/containers/{container_ident}/top

Display the running processes in a container.

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
   - ps_args: ps_args

Response
--------

.. rest_parameters:: parameters.yaml

  - ps_output: ps_output

Response Example
----------------

.. literalinclude:: samples/container-top-resp.json
   :language: javascript


List networks on a container
============================

.. rest_method:: GET /v1/containers/{container_ident}/network_list

List networks on a container

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

   - net_id: net_id
   - subnet_id: subnet_id
   - port_id: port_id
   - version: version
   - ip_address: ip_address
   - fixed_ips: fixed_ips

Response Example
----------------

.. literalinclude:: samples/container-network-list-resp.json
   :language: javascript

List Actions For Container
==========================

.. rest_method:: GET /v1/containers/{container_ident}/container_actions

List actions for a container

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

    - action: action
    - container_uuid: uuid
    - message: message
    - request_id: request_id_body
    - start_time: start_time
    - project_id: project_id_container_action
    - user_id: user_id

**Example List Actions For Container: JSON response**

.. literalinclude:: samples/container-actions-list-resp.json
    :language: javascript


Show Container Action Details
=============================

.. rest_method:: GET /v1/containers/{container_ident}/container_actions/{request_ident}

Show details for a container action.

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
    - request_ident: request_ident

Response
--------

.. rest_parameters:: parameters.yaml

    - action: action
    - container_uuid: uuid
    - message: message
    - project_id: project_id_container_action
    - request_id: request_id_body
    - start_time: start_time
    - user_id: user_id
    - events: container_action_events
    - events.event: event
    - events.start_time: event_start_time
    - events.finish_time: event_finish_time
    - events.result: event_result
    - events.traceback: event_traceback

**Example Show Container Action Details: JSON response**

.. literalinclude:: samples/container-action-get-resp.json
    :language: javascript
