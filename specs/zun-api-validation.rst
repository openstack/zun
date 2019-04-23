..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 https://creativecommons.org/licenses/by/3.0/legalcode

==============
API Validation
==============

`bp api-json-input-validation <https://blueprints.launchpad.net/zun/+spec/api-json-input-validation>`_

The purpose of this blueprint is to track the progress of validating the
request bodies sent to the Zun API server, accepting requests
that fit the resource schema and rejecting requests that do not fit the
schema. Depending on the content of the request body, the request should
be accepted or rejected consistently regardless of the resource the request
is for.

Problem Description
===================

Currently Zun validates each type of resource in request body by defining a
type class for that resource, although such approach is good but is not very
scalable. It also require conversion of request body to controller object and
vice versa.

Use Case: As an End User, I want to observe consistent API validation and
values passed to the Zun API server.

Proposed Change
===============

One possible way to validate the Zun API is to use jsonschema
(https://pypi.org/project/jsonschema/). A jsonschema validator object can
be used to check each resource against an appropriate schema for that
resource. If the validation passes, the request can follow the existing flow
of control to the resource manager. If the request body parameters fail the
validation specified by the resource schema, a validation error will be
returned from the server.

Example:
"Invalid input for field 'cpu'. The value is 'some invalid cpu value'.

We can build in some sort of truncation check if the value of the attribute is
too long. For example, if someone tries to pass in a 300 character name of
container we should check for that case and then only return a useful message,
instead of spamming the logs. Truncating some really long container name might
not help readability for the user, so return a message to the user with what
failed validation.

Example:
"Invalid input for field 'name'."

Some notes on doing this implementation:

* Common parameter types can be leveraged across all Zun resources. An
  example of this would be as follows::

    from zun.common.validation import parameter_types
    <snip>
    CREATE = {
        'type': 'object',
        'properties': {
            'name': parameter_types.name,
            'image': parameter_types.image,
            'command': parameter_types.command,
            <snip>
        },
        'required': ['image'],
        'additionalProperties': True,
    }

* The validation can take place at the controller layer.

* When adding a new extension to Zun, the new extension must be proposed
  with its appropriate schema.

Alternatives
------------

`Voluptuous <https://github.com/alecthomas/voluptuous>`_ might be another
option for input validation.

Data Model Impact
-----------------

This blueprint shouldn't require a database migration or schema change.

REST API Impact
---------------

This blueprint shouldn't affect the existing API.

Security Impact
---------------

None

Notifications Impact
--------------------

None

Other End User Impact
---------------------

None

Performance Impact
------------------

Changes required for request validation do not require any locking mechanisms.

Other Deployer Impact
---------------------

None

Developer Impact
----------------

This will require developers contributing new extensions to Zun to have
a proper schema representing the extension's API.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
pksingh (Pradeep Kumar Singh <ps4openstack@gmail.com>)

Work Items
----------

1. Initial validator implementation, which will contain common validator code
   designed to be shared across all resource controllers validating request
   bodies.
2. Introduce validation schemas for existing core API resources.
3. Enforce validation on proposed core API additions and extensions.

Dependencies
============

None

Testing
=======

Tempest tests can be added as each resource is validated against its schema.

Documentation Impact
====================

None

References
==========

Useful Links:

* [Understanding JSON Schema] (https://spacetelescope.github.io/understanding-json-schema/reference/object.html)

* [Nova Validation Examples] (https://opendev.org/openstack/nova/src/branch/master/nova/api/validation)

* [JSON Schema on PyPI] (https://pypi.org/project/jsonschema/)

* [JSON Schema core definitions and terminology] (https://tools.ietf.org/html/draft-zyp-json-schema-04)

* [JSON Schema Documentation] (https://json-schema.org/documentation.html)
