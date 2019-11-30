===================================
Legacy Init Script for Ubuntu 14.04
===================================

#. Clone the Zun repository:

   .. code-block:: console

      $ git clone https://opendev.org/openstack/zun.git

#. Enable and start zun-api:

   .. code-block:: console

      # cp zun/contrib/legacy-ubuntu-init/etc/init/zun-api.conf \
        /etc/init/zun-api.conf
      # start zun-api

#. Enable and start zun-wsproxy:

   .. code-block:: console

      # cp zun/contrib/legacy-ubuntu-init/etc/init/zun-wsproxy.conf \
        /etc/init/zun-wsproxy.conf
      # start zun-wsproxy

#. Enable and start zun-compute:

   .. code-block:: console

      # cp zun/contrib/legacy-ubuntu-init/etc/init/zun-compute.conf \
        /etc/init/zun-compute.conf
      # start zun-compute

#. Verify that zun services are running:

   .. code-block:: console

      # status zun-api
      # status zun-wsproxy
      # status zun-compute
