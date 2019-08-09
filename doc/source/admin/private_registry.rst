===========================================
How to use private docker registry with Zun
===========================================

Zun by default pull container images from Docker Hub.
However, it is possible to configure Zun to pull images from a
private registry.

This document provides an example to deploy and configure a
docker registry for Zun. For a comprehensive guide about deploying
a docker registry, see `here <https://docs.docker.com/registry/deploying/>`_

Deploy Private Docker Registry
==============================
A straightforward approach to install a private docker registry is to
deploy it as a Zun container:

.. code-block:: console

    $ openstack appcontainer create \
        --restart always \
        --expose-port 443 \
        --name registry \
        --environment REGISTRY_HTTP_ADDR=0.0.0.0:443 \
        --environment REGISTRY_HTTP_TLS_CERTIFICATE=/domain.crt \
        --environment REGISTRY_HTTP_TLS_KEY=/domain.key \
        registry:2

.. note::

   Depending on the configuration of your tenant network, you might need
   to make sure the container is accessible from other tenants of your cloud.
   For example, you might need to associate a floating IP to the container.

In order to make your registry accessible to external hosts,
you must use a TLS certificate (issued by a certificate issuer) or create
self-signed certificates. This document shows you how to generate and use
self-signed certificates:

.. code-block:: console

    $ mkdir -p certs
    $ cat > certs/domain.conf <<EOF
    [req]
    distinguished_name = req_distinguished_name
    req_extensions     = req_ext
    prompt = no
    [req_distinguished_name]
    CN = zunregistry.com
    [req_ext]
    subjectAltName = IP:172.24.4.49
    EOF
    $ openssl req \
        -newkey rsa:4096 -nodes -sha256 -keyout certs/domain.key \
        -x509 -days 365 -out certs/domain.crt -config certs/domain.conf

.. note::

   Replace ``zunregistry.com`` with the domain name of your registry.

.. note::

   Replace ``172.24.4.49`` with the IP address of your registry.

.. note::

   You need to make sure the domain name (i.e. ``zunregistry.com``)
   will be resolved to the IP address (i.e. ``172.24.4.49``).
   For example, you might need to edit ``/etc/hosts`` accordingly.

Copy the certificates to registry:

.. code-block:: console

    $ openstack appcontainer cp certs/domain.key registry:/
    $ openstack appcontainer cp certs/domain.crt registry:/

Configure docker daemon to accept the certificates:

.. code-block:: console

    # mkdir -p /etc/docker/certs.d/zunregistry.com
    # cp certs/domain.crt /etc/docker/certs.d/zunregistry.com/ca.crt

.. note::

   Replace ``zunregistry.com`` with the domain name of your registry.

.. note::

   Perform this steps in every compute nodes.

Start the registry:

.. code-block:: console

    $ openstack appcontainer start registry

Verify the registry is working:

.. code-block:: console

    $ docker pull ubuntu:16.04
    $ docker tag ubuntu:16.04 zunregistry.com/my-ubuntu
    $ docker push zunregistry.com/my-ubuntu
    $ openstack appcontainer run --interactive zunregistry.com/my-ubuntu /bin/bash

.. note::

   Replace ``zunregistry.com`` with the domain name of your registry.
