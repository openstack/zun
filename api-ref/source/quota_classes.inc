.. -*- rst -*-

=====================
 Manage Quota Classes
=====================

Get, updates quota classes

Create or Update Quotas for Quota Class
=======================================

.. rest_method:: PUT /v1/quota_classes/{quota_class_name}

Update the quotas for the Quota Class. If the requested Quota Class is not
found in the DB, then the API will create the one.

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

   - quota_class_name: quota_class_name
   - containers: container-request
   - memory: memory-request
   - cpu: cpu-request
   - disk: disk-request

Request Example
---------------

.. literalinclude:: samples/quota-classes-update-req.json
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

.. literalinclude:: samples/quota-classes-update-resp.json
   :language: javascript

List quotas for Quota Class
===========================

.. rest_method:: GET /v1/quota_classes/{quota_class_name}

List quotas for Quota Class

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

   - quota_class_name: quota_class_name

Response
--------

.. rest_parameters:: parameters.yaml

   - containers: container-response
   - memory: memory-response
   - cpu: cpu-response
   - disk: disk-response

Response Example
----------------

.. literalinclude:: samples/quota-classes-get-resp.json
   :language: javascript
