..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============================
Welcome to Zun's documentation!
===============================

What is Zun?
=============

Zun is an OpenStack Container service. It aims to provide an API service for
running application containers without the need to manage servers or clusters.

It requires the following additional OpenStack services for basic function:

* `Keystone <https://docs.openstack.org/keystone/latest/>`__
* `Neutron <https://docs.openstack.org/neutron/latest/>`__
* `Kuryr-libnetwork <https://docs.openstack.org/kuryr-libnetwork/latest/>`__

It can also integrate with other services to include:

* `Cinder <https://docs.openstack.org/cinder/latest/>`__
* `Heat <https://docs.openstack.org/heat/latest/>`__
* `Glance <https://docs.openstack.org/glance/latest/>`__

For End Users
=============

As an end user of Zun, you'll use Zun to create and manage containerized
workload with either tools or the API directly.
All end user (and some administrative) features of Zun are exposed via a REST
API, which can be consumed directly. The following resources will help you get
started with consuming the API directly.

* `API Reference <http://developer.openstack.org/api-ref/application-container/>`_

Alternatively, end users can consume the REST API via various tools or SDKs.
These tools are collected below.

* `Horizon
  <https://docs.openstack.org/zun-ui/latest/>`_: The
  official web UI for the OpenStack Project.
* `OpenStack Client
  <https://docs.openstack.org/python-openstackclient/latest/>`_: The official
  CLI for OpenStack Projects.
* `Zun Client
  <https://docs.openstack.org/python-zunclient/latest/>`_: The Python client
  for consuming the Zun's API.

For Operators
=============

Installation
------------

The detailed install guide for Zun. A functioning Zun will also require
having installed `Keystone
<https://docs.openstack.org/keystone/latest/install/>`__, `Neutron
<https://docs.openstack.org/neutron/latest/install/>`__, and `Kuryr-libnetwork
<https://docs.openstack.org/kuryr-libnetwork/latest/install/>`__.
Please ensure that you follow their install guides first.

.. toctree::
   :maxdepth: 2

   install/index

For Contributors
================

If you are new to Zun, this should help you quickly setup the development
environment and get started.

.. toctree::
   :glob:
   :maxdepth: 2

   contributor/quickstart

There are also a number of technical references on various topics.
These are collected below.

.. toctree::
   :glob:
   :maxdepth: 2

   contributor/index

Reference Material
==================

.. toctree::
   :glob:
   :maxdepth: 2

   cli/index
   admin/index
   configuration/index
   user/filter-scheduler
   reference/api-microversion-history

Search
======

* :ref:`Zun document search <search>`: Search the contents of this document.
* `OpenStack wide search <https://docs.openstack.org>`_: Search the wider
  set of OpenStack documentation, including forums.
