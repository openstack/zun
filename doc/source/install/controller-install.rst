Install and configure controller node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container service
on the controller node for Ubuntu 16.04 (LTS) and CentOS 7.

Prerequisites
-------------

Before you install and configure Zun, you must create a database,
service credentials, and API endpoints.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``zun`` database:

     .. code-block:: console

        MariaDB [(none)] CREATE DATABASE zun;

   * Grant proper access to the ``zun`` database:

     .. code-block:: console

        MariaDB [(none)]> GRANT ALL PRIVILEGES ON zun.* TO 'zun'@'localhost' \
          IDENTIFIED BY 'ZUN_DBPASS';
        MariaDB [(none)]> GRANT ALL PRIVILEGES ON zun.* TO 'zun'@'%' \
          IDENTIFIED BY 'ZUN_DBPASS';

     Replace ``ZUN_DBPASS`` with a suitable password.

   * Exit the database access client.

#. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   * Create the ``zun`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt zun
        User Password:
        Repeat User Password:
        +-----------+----------------------------------+
        | Field     | Value                            |
        +-----------+----------------------------------+
        | domain_id | e0353a670a9e496da891347c589539e9 |
        | enabled   | True                             |
        | id        | ca2e175b851943349be29a328cc5e360 |
        | name      | zun                              |
        +-----------+----------------------------------+

   * Add the ``admin`` role to the ``zun`` user:

     .. code-block:: console

        $ openstack role add --project service --user zun admin

     .. note::

        This command provides no output.

   * Create the ``zun`` service entities:

     .. code-block:: console

        $ openstack service create --name zun \
            --description "Container Service" container
        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | description | Container Service                |
        | enabled     | True                             |
        | id          | 727841c6f5df4773baa4e8a5ae7d72eb |
        | name        | zun                              |
        | type        | container                        |
        +-------------+----------------------------------+

#. Create the Container service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
          container public http://controller:9517/v1
      +--------------+-----------------------------------------+
      | Field        | Value                                   |
      +--------------+-----------------------------------------+
      | enabled      | True                                    |
      | id           | 3f4dab34624e4be7b000265f25049609        |
      | interface    | public                                  |
      | region       | RegionOne                               |
      | region_id    | RegionOne                               |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb        |
      | service_name | zun                                     |
      | service_type | container                               |
      | url          | http://controller:9517/v1               |
      +--------------+-----------------------------------------+

      $ openstack endpoint create --region RegionOne \
          container internal http://controller:9517/v1
      +--------------+-----------------------------------------+
      | Field        | Value                                   |
      +--------------+-----------------------------------------+
      | enabled      | True                                    |
      | id           | 9489f78e958e45cc85570fec7e836d98        |
      | interface    | internal                                |
      | region       | RegionOne                               |
      | region_id    | RegionOne                               |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb        |
      | service_name | zun                                     |
      | service_type | container                               |
      | url          | http://controller:9517/v1               |
      +--------------+-----------------------------------------+

      $ openstack endpoint create --region RegionOne \
          container admin http://controller:9517/v1
      +--------------+-----------------------------------------+
      | Field        | Value                                   |
      +--------------+-----------------------------------------+
      | enabled      | True                                    |
      | id           | 76091559514b40c6b7b38dde790efe99        |
      | interface    | admin                                   |
      | region       | RegionOne                               |
      | region_id    | RegionOne                               |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb        |
      | service_name | zun                                     |
      | service_type | container                               |
      | url          | http://controller:9517/v1               |
      +--------------+-----------------------------------------+

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

      # apt-get install python3-pip git

   For CentOS, run:

   .. code-block:: console

     # yum install python3-pip git python3-devel libffi-devel gcc openssl-devel

#. Clone and install zun:

   .. code-block:: console

      # cd /var/lib/zun
      # git clone https://opendev.org/openstack/zun.git
      # chown -R zun:zun zun
      # cd zun
      # pip3 install -r requirements.txt
      # python3 setup.py install

#. Generate a sample configuration file:

   .. code-block:: console

      # su -s /bin/sh -c "oslo-config-generator \
          --config-file etc/zun/zun-config-generator.conf" zun
      # su -s /bin/sh -c "cp etc/zun/zun.conf.sample \
          /etc/zun/zun.conf" zun

#. Copy api-paste.ini:

   .. code-block:: console

      # su -s /bin/sh -c "cp etc/zun/api-paste.ini /etc/zun" zun

#. Edit the ``/etc/zun/zun.conf``:

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: ini

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

   * In the ``[api]`` section, configure the IP address that Zun API
     server is going to listen:

     .. code-block:: ini

        [api]
        ...
        host_ip = 10.0.0.11
        port = 9517

     Replace ``10.0.0.11`` with the management interface IP address
     of the controller node if different.

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

     Replace ZUN_PASS with the password you chose for the zun user in the
     Identity service.

   * In the ``[oslo_concurrency]`` section, configure the ``lock_path``:

     .. code-block:: ini

        [oslo_concurrency]
        ...
        lock_path = /var/lib/zun/tmp

   * In the ``[oslo_messaging_notifications]`` section, configure the
     ``driver``:

     .. code-block:: ini

        [oslo_messaging_notifications]
        ...
        driver = messaging

   * In the ``[websocket_proxy]`` section, configure the IP address that
     the websocket proxy is going to listen to:

     .. code-block:: ini

        [websocket_proxy]
        ...
        wsproxy_host = 10.0.0.11
        wsproxy_port = 6784
        base_url = ws://controller:6784/

     .. note::

        This ``base_url`` will be used by end users to access the console of
        their containers so make sure this URL is accessible from your
        intended users and the port ``6784`` is not blocked by firewall.

     Replace ``10.0.0.11`` with the management interface IP address
     of the controller node if different.

   .. note::

      Make sure that ``/etc/zun/zun.conf`` still have the correct
      permissions. You can set the permissions again with:

      # chown zun:zun /etc/zun/zun.conf

#. Populate Zun database:

   .. code-block:: console

      # su -s /bin/sh -c "zun-db-manage upgrade" zun

Finalize installation
---------------------

#. Create an upstart config, it could be named as
   ``/etc/systemd/system/zun-api.service``:

   .. note::

      CentOS might install binary files into ``/usr/bin/``.
      If it does, replace ``/usr/local/bin/`` directory with the correct
      in the following example files.

   .. code-block:: bash

      [Unit]
      Description = OpenStack Container Service API

      [Service]
      ExecStart = /usr/local/bin/zun-api
      User = zun

      [Install]
      WantedBy = multi-user.target

#. Create an upstart config, it could be named as
   ``/etc/systemd/system/zun-wsproxy.service``:

   .. code-block:: bash

      [Unit]
      Description = OpenStack Container Service Websocket Proxy

      [Service]
      ExecStart = /usr/local/bin/zun-wsproxy
      User = zun

      [Install]
      WantedBy = multi-user.target

#. Enable and start zun-api and zun-wsproxy:

   .. code-block:: console

      # systemctl enable zun-api
      # systemctl enable zun-wsproxy

   .. code-block:: console

      # systemctl start zun-api
      # systemctl start zun-wsproxy

#. Verify that zun-api and zun-wsproxy services are running:

   .. code-block:: console

      # systemctl status zun-api
      # systemctl status zun-wsproxy

