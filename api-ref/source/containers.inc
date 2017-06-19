.. -*- rst -*-

===================
 Manage Containers
===================

Lists, creates, shows details for, updates, and deletes containers.

Create new container
====================

.. rest_method:: POST /v1/containers/

Create new container.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

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
