.. -*- rst -*-

==================
Manage zun host
==================

List all compute hosts
========================================

.. rest_method::  GET /v1/hosts

Enables administrative users to list all Zun container hosts.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - hosts: host_list
   - uuid: uuid
   - hostname: hostname
   - mem_total: mem_total
   - cpus: cpus
   - os: os
   - labels: labels

Response Example
----------------

.. literalinclude:: samples/host-get-all-resp.json
   :language: javascript
