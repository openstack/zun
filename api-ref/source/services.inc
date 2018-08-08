.. -*- rst -*-

==================
Manage Zun service
==================

Show service status
===================

.. rest_method::  GET /v1/services

Enables administrative users to view details for all Zun services.

Service status details include service id, binary,
host, report count, creation time, last updated time, health status, and
the reason for disabling service.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - services: services
   - binary: binary
   - availability_zone: availability_zone
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


Delete service
==============

.. rest_method::  DELETE /v1/services

Delete the specified Zun service.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - binary: binary
  - host: host

Response Parameters
-------------------

If successful, this method does not return content in the response body.


Enable service
==============

.. rest_method::  PUT /v1/services/enable

Enable the specified Zun service.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - binary: binary
  - host: host

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - service: service
   - host: host
   - binary: binary
   - disabled: disabled
   - disabled_reason: disabled_reason

Response Example
----------------

.. literalinclude:: samples/service-enable-resp.json
   :language: javascript


Disable service
===============

.. rest_method::  PUT /v1/services/disable

Disable the specified Zun service.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - binary: binary
  - host: host
  - disabled_reason: disabled_reason

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - service: service
   - host: host
   - binary: binary
   - disabled: disabled
   - disabled_reason: disabled_reason

Response Example
----------------

.. literalinclude:: samples/service-disable-resp.json
   :language: javascript


Force down service
==================

.. rest_method::  PUT /v1/services/force_down

Force the specified Zun service to down or unset it.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - binary: binary
  - host: host
  - forced_down: forced_down

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - service: service
   - host: host
   - binary: binary
   - forced_down: forced_down

Response Example
----------------

.. literalinclude:: samples/service-forcedown-resp.json
   :language: javascript
