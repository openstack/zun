==========================
Container service overview
==========================

The Container service consists of the following components:

``zun-api``
  An OpenStack-native REST API that processes API requests by sending
  them to the ``zun-compute`` over Remote Procedure Call (RPC).

``zun-compute``
  A worker daemon that creates and terminates containers or capsules (pods)
  through container engine API. Manage containers, capsules and compute
  resources in local host.

``zun-wsproxy``
  Provides a proxy for accessing running containers through a websocket
  connection.

``zun-cni-daemon``
  Provides a CNI daemon service that provides implementation for the Zun CNI
  plugin.

Optionally, one may wish to utilize the following associated projects for
additional functionality:

python-zunclient_
  A command-line interface (CLI) and python bindings for interacting with the
  Container service.

zun-ui_
  The Horizon plugin for providing Web UI for Zun.

.. _python-zunclient: https://docs.openstack.org/python-zunclient/latest/
.. _zun-ui: https://docs.openstack.org/zun-ui/latest/
