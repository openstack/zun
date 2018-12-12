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
   - architecture: host-architecture
   - cpus: host-cpus
   - cpu_used: host-cpu_used
   - disk_used: host-disk_used
   - disk_total: host-disk_total
   - hostname: host-hostname
   - kernel_version: host-kernel_version
   - labels: host-labels
   - mem_used: host-mem_used
   - mem_total: host-mem_total
   - os: host-os
   - os_type: host-os_type
   - total_containers: host-total_containers
   - uuid: host-uuid
   - enable_cpu_pinning: enable_cpu_pinning

Response Example
----------------

.. literalinclude:: samples/host-get-all-resp.json
   :language: javascript

Show details of a host
===========================

.. rest_method:: GET /v1/hosts/{host_ident}

Get all information of a host in Zun.

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

  - host_ident: host_ident

Response
--------

.. rest_parameters:: parameters.yaml

   - architecture: host-architecture
   - cpus: host-cpus
   - cpu_used: host-cpu_used
   - disk_used: host-disk_used
   - disk_total: host-disk_total
   - hostname: host-hostname
   - kernel_version: host-kernel_version
   - labels: host-labels
   - mem_used: host-mem_used
   - mem_total: host-mem_total
   - os: host-os
   - os_type: host-os_type
   - total_containers: host-total_containers
   - uuid: host-uuid
   - enable_cpu_pinning: enable_cpu_pinning

Response Example
----------------

.. literalinclude:: samples/host-get-resp.json
   :language: javascript
