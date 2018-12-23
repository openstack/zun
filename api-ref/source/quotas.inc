.. -*- rst -*-

==============
 Manage Quotas
==============

Gets, updates, gets default and deletes quotas for a project.

Update quotas for a project
===========================

.. rest_method:: PUT /v1/quotas/{project_id}

Update the quotas for a project

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id
   - containers: container-request
   - memory: memory-request
   - cpu: cpu-request
   - disk: disk-request

Request Example
---------------

.. literalinclude:: samples/quotas-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - containers: container-response
   - memory: memory-response
   - cpu: cpu-response
   - disk: disk-response

Response Example
----------------

.. literalinclude:: samples/quotas-update-resp.json
   :language: javascript

Get quotas for a project
========================

.. rest_method:: GET /v1/quotas/{project_id}

Get quotas for a project

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id

Response
--------

.. rest_parameters:: parameters.yaml

   - usages: usages
   - containers: container-response
   - memory: memory-response
   - cpu: cpu-response
   - disk: disk-response

Response Example
----------------

.. literalinclude:: samples/quotas-get-resp.json
   :language: javascript

Get Default quotas for a project
================================

.. rest_method:: GET /v1/quotas/{project_id}/defaults

Get the default quotas for a project

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id

Response
--------

.. rest_parameters:: parameters.yaml

   - usages: usages
   - containers: container-response
   - memory: memory-response
   - cpu: cpu-response
   - disk: disk-response

Response Example
----------------

.. literalinclude:: samples/quotas-get-defaults-resp.json
   :language: javascript

Revert Quotas to defaults
=========================

.. rest_method:: DELETE /v1/quotas/{project_id}

Reverts the quotas to default values for a project

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id

Response
--------

There is no body content for the response of a successful DELETE operation.
