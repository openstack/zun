REST API Version History
========================

This documents the changes made to the REST API with every
microversion change. The description for each version should be a
verbose one which has enough information to be suitable for use in
user documentation.

1.1
---

  This is the initial version of the v1.1 API which supports
  microversions. The v1.1 API is from the REST API users's point of
  view exactly the same as v1.0 except with strong input validation.

  A user can specify a header in the API request::

    OpenStack-API-Version: <version>

  where ``<version>`` is any valid api version for this API.

  If no version is specified then the API will behave as if a version
  request of v1.1 was requested.

1.2
---

  Add a new attribute 'nets' to the request to create a container.
  Users can use this attribute to specify one or multiple networks for
  the container. Each network could specify the neutron network, neutron
  port, or a v4/v6 IP address. For examples:

    [{u'port': u'1234567'}]
    [{u'v4-fixed-ip': u'127.0.0.1'}]
    [{u'network': u'test'}]
    [{u'network': u'test2'}]
    [{u'v6-fixed-ip': u'2f:33:45'}]
