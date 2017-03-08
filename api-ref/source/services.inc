.. -*- rst -*-

==================
Manage Zun service
==================

Show container management service status
========================================

.. rest_method::  GET /v1/services

Enables administrative users to view details for all Zun services.

Container management service status details include service id, binary,
host, report count, creation time, last updated time, health status, and
the reason for disabling service.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - services: services
   - binary: binary
   - created_at: created_at
   - state: state
   - report_count: report_count
   - updated_at: updated_at
   - host: host
   - disabled_reason: disabled_reason
   - id: id_s

Response Example
----------------

.. literalinclude:: samples/service-get-resp.json
   :language: javascript

