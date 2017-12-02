Install and configure a compute node for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This section describes how to install and configure the Container service on a
compute node for Ubuntu 16.04 (LTS).

Prerequisites
-------------

Before you install and configure Zun, you must have Docker and
Kuryr-libnetwork installed properly in the compute node. Refer `Get Docker
<https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_
for Docker installation and `Kuryr libnetwork installation guide
<https://docs.openstack.org/kuryr-libnetwork/latest/install>`_

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

#. Edit the ``/etc/zun/zun.conf``:

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: ini

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

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
        auth_uri = http://controller:5000
        project_domain_name = default
        project_name = service
        user_domain_name = default
        password = ZUN_PASS
        username = zun
        auth_url = http://controller:35357
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
        auth_uri = http://controller:5000
        project_domain_name = default
        project_name = service
        user_domain_name = default
        password = ZUN_PASS
        username = zun
        auth_url = http://controller:35357
        auth_type = password

     Replace ZUN_PASS with the password you chose for the zun user in the
     Identity service.

   * In the ``[websocket_proxy]`` section, configure the URL of the websocket
     proxy. This URL must match the websocket configuration in controller
     node:

     .. code-block:: ini

        [websocket_proxy]
        ...
        base_url = ws://controller:6784/

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
     Configure docker to listen to port 2375 as well as the the default
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
     Set capability_scope to global:

     .. code-block:: ini

        [DEFAULT]
        ...
        capability_scope = global

   * Restart Kuryr-libnetwork:

     .. code-block:: console

        # systemctl restart kuryr-libnetwork

Finalize installation
---------------------

#. Create an upstart config, it could be named as
   ``/etc/systemd/system/zun-compute.service``:

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
