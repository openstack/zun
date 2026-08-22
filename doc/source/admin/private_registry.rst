=================================================
How to use Private Distribution Registry with Zun
=================================================

.. note::

   Registry (now CNCF Distribution)

   The Docker Registry served as the open-source implementation
   of a container image registry. It was donated to the
   Cloud Native Computing Foundation (CNCF) in 2019 and is
   maintained under the name "Distribution."
   It remains a cornerstone for managing and distributing
   container images.

Zun pulls container images from Docker Hub by default.
However, it is possible to configure Zun to pull images from a
Private Distribution Registry.

This document provides an example to deploy and configure a
Distribution Registry for Zun. For a comprehensive guide
about deploying a Distribution Registry, see `here <https://distribution.github.io/distribution/>`_.

Deploy Private Distribution Registry
====================================

A straightforward way to deploy a Private Distribution Registry
is to run it as a Zun container:

.. code-block:: console

    $ openstack appcontainer create \
        --restart always \
        --expose-port 443 \
        --name registry \
        --environment REGISTRY_HTTP_ADDR=0.0.0.0:443 \
        --environment REGISTRY_HTTP_TLS_CERTIFICATE=/domain.crt \
        --environment REGISTRY_HTTP_TLS_KEY=/domain.key \
        registry:3

.. note::

   Depending on the configuration of your tenant network, you might need
   to make sure the container is accessible from other tenants of your cloud.
   For example, you might need to associate a floating IP to the container.

In order to make your registry accessible to external hosts,
you must use a TLS certificate issued by a trusted Certificate Authority
(CA), or generate a self-signed certificate. This document shows
you how to generate and use self-signed certificates:

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

Copy the certificates into the registry container:

.. code-block:: console

    $ openstack appcontainer cp certs/domain.key registry:/
    $ openstack appcontainer cp certs/domain.crt registry:/

Configure the Docker daemon to trust the registry certificate:

.. code-block:: console

    # mkdir -p /etc/docker/certs.d/zunregistry.com
    # cp certs/domain.crt /etc/docker/certs.d/zunregistry.com/ca.crt

.. note::

   Replace ``zunregistry.com`` with the domain name of your registry.

.. note::

   Perform these steps on every compute node.

Start the registry:

.. code-block:: console

    $ openstack appcontainer start registry

Verify that the registry is working:

.. code-block:: console

    $ docker pull ubuntu:24.04
    $ docker tag ubuntu:24.04 zunregistry.com/my-ubuntu:24.04
    $ docker push zunregistry.com/my-ubuntu:24.04
    $ openstack appcontainer run --interactive zunregistry.com/my-ubuntu:24.04 /bin/bash

.. note::

   Replace ``zunregistry.com`` with the domain name of your registry.
