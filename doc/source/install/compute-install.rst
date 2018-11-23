Install and configure a compute node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Compute service on a
compute node.

.. note::

   This section assumes that you are following the instructions in this guide
   step-by-step to configure the first compute node. If you want to configure
   additional compute nodes, prepare them in a similar fashion. Each additional
   compute node requires a unique IP address.

Prerequisites
-------------

Before you install and configure Zun, you must have Docker and
Kuryr-libnetwork installed properly in the compute node, and have Etcd
installed properly in the controller node. Refer `Get Docker
<https://docs.docker.com/install/#supported-platforms>`_
for Docker installation and `Kuryr libnetwork installation guide
<https://docs.openstack.org/kuryr-libnetwork/latest/install>`_,
`Etcd installation guide
<https://docs.openstack.org/install-guide/environment-etcd.html>`_

Install and configure components
--------------------------------

#. Create zun user and necessary directories:

   * Create user:

     .. code-block:: console

        # groupadd --system zun
        # useradd --home-dir "/var/lib/zun" \
              --create-home \
              --system \
              --shell /bin/false \
              -g zun \
              zun

   * Create directories:

     .. code-block:: console

        # mkdir -p /etc/zun
        # chown zun:zun /etc/zun

#. Install the following dependencies:

   For Ubuntu, run:

   .. code-block:: console

      # apt-get install python-pip git

   For CentOS, run:

   .. code-block:: console

     # yum install python-pip git python-devel libffi-devel gcc openssl-devel

   .. note::

     ``python-pip`` package is not in CentOS base repositories,
     may need to install EPEL repository in order to have
     ``python-pip`` available.

#. Clone and install zun:

   .. code-block:: console

      # cd /var/lib/zun
      # git clone https://git.openstack.org/openstack/zun.git
      # chown -R zun:zun zun
      # cd zun
      # pip install -r requirements.txt
      # python setup.py install

#. Generate a sample configuration file:

   .. code-block:: console

      # su -s /bin/sh -c "oslo-config-generator \
          --config-file etc/zun/zun-config-generator.conf" zun
      # su -s /bin/sh -c "cp etc/zun/zun.conf.sample \
          /etc/zun/zun.conf" zun
      # su -s /bin/sh -c "cp etc/zun/rootwrap.conf \
          /etc/zun/rootwrap.conf" zun
      # su -s /bin/sh -c "mkdir -p /etc/zun/rootwrap.d" zun
      # su -s /bin/sh -c "cp etc/zun/rootwrap.d/* \
          /etc/zun/rootwrap.d/" zun

#. Configure sudoers for ``zun`` users:

   .. note::

      CentOS install binary files into ``/usr/bin/``,
      replace ``/usr/local/bin/`` directory with the correct
      in the following command.

   .. code-block:: console

      # echo "zun ALL=(root) NOPASSWD: /usr/local/bin/zun-rootwrap \
          /etc/zun/rootwrap.conf *" | sudo tee /etc/sudoers.d/zun-rootwrap

#. Edit the ``/etc/zun/zun.conf``:

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: ini

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

   * In the ``[DEFAULT]`` section,
     configure the path that is used by Zun to store the states:

     .. code-block:: ini

        [DEFAULT]
        ...
        state_path = /var/lib/zun

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://zun:ZUN_DBPASS@controller/zun

     Replace ``ZUN_DBPASS`` with the password you chose for
     the zun database.

   * In the ``[keystone_auth]`` section, configure
     Identity service access:

     .. code-block:: ini

        [keystone_auth]
        memcached_servers = controller:11211
        www_authenticate_uri = http://controller:5000
        project_domain_name = default
        project_name = service
        user_domain_name = default
        password = ZUN_PASS
        username = zun
        auth_url = http://controller:5000
        auth_type = password
        auth_version = v3
        auth_protocol = http
        service_token_roles_required = True
        endpoint_type = internalURL


   * In the ``[keystone_authtoken]`` section, configure
     Identity service access:

     .. code-block:: ini

        [keystone_authtoken]
        ...
        memcached_servers = controller:11211
        www_authenticate_uri= http://controller:5000
        project_domain_name = default
        project_name = service
        user_domain_name = default
        password = ZUN_PASS
        username = zun
        auth_url = http://controller:5000
        auth_type = password

     Replace ZUN_PASS with the password you chose for the zun user in the
     Identity service.

   * In the ``[oslo_concurrency]`` section, configure the ``lock_path``:

     .. code-block:: ini

        [oslo_concurrency]
        ...
        lock_path = /var/lib/zun/tmp

   .. note::

      Make sure that ``/etc/zun/zun.conf`` still have the correct
      permissions. You can set the permissions again with:

      # chown zun:zun /etc/zun/zun.conf

#. Configure Docker and Kuryr:

   * Create the directory ``/etc/systemd/system/docker.service.d``

     .. code-block:: console

        # mkdir -p /etc/systemd/system/docker.service.d

   * Create the file ``/etc/systemd/system/docker.service.d/docker.conf``.
     Configure docker to listen to port 2375 as well as the default
     unix socket. Also, configure docker to use etcd3 as storage backend:

     .. code-block:: ini

        [Service]
        ExecStart=
        ExecStart=/usr/bin/dockerd --group zun -H tcp://compute1:2375 -H unix:///var/run/docker.sock --cluster-store etcd://controller:2379

   * Restart Docker:

     .. code-block:: console

        # systemctl daemon-reload
        # systemctl restart docker

   * Edit the Kuryr config file ``/etc/kuryr/kuryr.conf``.
     Set ``capability_scope`` to ``global`` and
     ``process_external_connectivity`` to ``False``:

     .. code-block:: ini

        [DEFAULT]
        ...
        capability_scope = global
        process_external_connectivity = False

   * Restart Kuryr-libnetwork:

     .. code-block:: console

        # systemctl restart kuryr-libnetwork

Finalize installation
---------------------

#. Create an upstart config, it could be named as
   ``/etc/systemd/system/zun-compute.service``:

   .. note::

      CentOS install binary files into ``/usr/bin/``,
      replace ``/usr/local/bin/`` directory with the correct
      in the following example file.

   .. code-block:: bash

      [Unit]
      Description = OpenStack Container Service Compute Agent

      [Service]
      ExecStart = /usr/local/bin/zun-compute
      User = zun

      [Install]
      WantedBy = multi-user.target

#. Enable and start zun-compute:

   .. code-block:: console

      # systemctl enable zun-compute
      # systemctl start zun-compute

#. Verify that zun-compute services are running:

   .. code-block:: console

      # systemctl status zun-compute

