.. -*- rst -*-

=================
 Zun Base URLs
=================

All API calls through the rest of this document require authentication
with the OpenStack Identity service. They also required a ``url`` that
is extracted from the Identity token of type
``container``. This will be the root url that every call below will be
added to build a full path.

Note that if using OpenStack Identity service API v2, ``url`` can be
represented via ``adminURL``, ``internalURL`` or ``publicURL`` in endpoint
catalog. In Identity service API v3, ``url`` is represented with field
``interface`` including ``admin``, ``internal`` and ``public``.

For instance, if the ``url`` is
``http://my-zun-url.org/zun/v1`` then the full API call for
``/containers`` is ``http://my-zun-url.org/zun/v1/containers``.

Depending on the deployment the containers service
url might be http or https, a custom port, a custom path, and include your
project id. The only way to know the urls for your deployment is by using the
service catalog. The containers service URL should never be
hard coded in applications, even if they are only expected to work at a
single site. It should always be discovered from the Identity token.

As such, for the rest of this document we will be using short hand
where ``GET /containers`` really means
``GET {your_zun_url}/containers``.
