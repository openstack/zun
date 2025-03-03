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
Kuryr-libnetwork installed properly in the compute node. Refer `Get Docker
<https://docs.docker.com/engine/install#supported-platforms>`_
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

   * Create CNI directories:

     .. code-block:: console

        # mkdir -p /etc/cni/net.d
        # chown zun:zun /etc/cni/net.d

#. Install the following dependencies:

   For Ubuntu, run:

   .. code-block:: console

      # apt-get install python3-pip git numactl

   For CentOS, run:

   .. code-block:: console

     # yum install python3-pip git python3-devel libffi-devel gcc openssl-devel numactl

#. Clone and install zun:

   .. code-block:: console

      # cd /var/lib/zun
      # git clone https://opendev.org/openstack/zun.git
      # chown -R zun:zun zun
      # git config --global --add safe.directory /var/lib/zun/zun
      # cd zun
      # pip3 install -r requirements.txt
      # python3 setup.py install

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
      # su -s /bin/sh -c "cp etc/cni/net.d/* /etc/cni/net.d/" zun

#. Configure sudoers for ``zun`` users:

   .. note::

      CentOS might install binary files into ``/usr/bin/``.
      If it does, replace ``/usr/local/bin/`` directory with the correct
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

   * (Optional) If you want to run both containers and nova instances in
     this compute node, in the ``[compute]`` section,
     configure the ``host_shared_with_nova``:

     .. code-block:: ini

        [compute]
        ...
        host_shared_with_nova = true

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
     unix socket:

     .. code-block:: ini

        [Service]
        ExecStart=
        ExecStart=/usr/bin/dockerd --group zun -H tcp://compute1:2375 -H unix:///var/run/docker.sock

   * Restart Docker:

     .. code-block:: console

        # systemctl daemon-reload
        # systemctl restart docker

   * Edit the Kuryr config file ``/etc/kuryr/kuryr.conf``.
     Set ``process_external_connectivity`` to ``False``:

     .. code-block:: ini

        [DEFAULT]
        ...
        process_external_connectivity = False

   * Restart Kuryr-libnetwork:

     .. code-block:: console

        # systemctl restart kuryr-libnetwork

#. Configure containerd:

   * Generate config file for containerd:

     .. code-block:: console

        # containerd config default > /etc/containerd/config.toml

   * Edit the ``/etc/containerd/config.toml``. In the ``[grpc]`` section,
     configure the ``gid`` as the group ID of the ``zun`` user:

     .. code-block:: ini

        [grpc]
          ...
          gid = ZUN_GROUP_ID

     Replace ``ZUN_GROUP_ID`` with the real group ID of ``zun`` user.
     You can retrieve the ID by (for example):

     .. code-block:: console

        # getent group zun | cut -d: -f3

     .. note::

        Make sure that ``/etc/containerd/config.toml`` still have the correct
        permissions. You can set the permissions again with:

        # chown zun:zun /etc/containerd/config.toml

   * Restart containerd:

     .. code-block:: console

        # systemctl restart containerd

#. Configure CNI:

   * Download and install the standard loopback plugin:

     .. code-block:: console

        # mkdir -p /opt/cni/bin
        # curl -L https://github.com/containernetworking/plugins/releases/download/v0.7.1/cni-plugins-amd64-v0.7.1.tgz \
              | tar -C /opt/cni/bin -xzvf - ./loopback

   * Install the Zun CNI plugin:

     .. code-block:: console

        # install -o zun -m 0555 -D /usr/local/bin/zun-cni /opt/cni/bin/zun-cni

     .. note::

        CentOS might install binary files into ``/usr/bin/``.
        If it does, replace ``/usr/local/bin/zun-cni`` with the correct path
        in the command above.

Finalize installation
---------------------

#. Create an upstart config for zun compute, it could be named as
   ``/etc/systemd/system/zun-compute.service``:

   .. note::

      CentOS might install binary files into ``/usr/bin/``.
      If it does, replace ``/usr/local/bin/`` directory with the correct
      in the following example file.

   .. code-block:: bash

      [Unit]
      Description = OpenStack Container Service Compute Agent

      [Service]
      ExecStart = /usr/local/bin/zun-compute
      User = zun

      [Install]
      WantedBy = multi-user.target

#. Create an upstart config for zun cni daemon, it could be named as
   ``/etc/systemd/system/zun-cni-daemon.service``:

   .. note::

      CentOS might install binary files into ``/usr/bin/``,
      If it does, replace ``/usr/local/bin/`` directory with the correct
      in the following example file.

   .. code-block:: bash

      [Unit]
      Description = OpenStack Container Service CNI daemon

      [Service]
      ExecStart = /usr/local/bin/zun-cni-daemon
      User = zun

      [Install]
      WantedBy = multi-user.target

#. Enable and start zun-compute:

   .. code-block:: console

      # systemctl enable zun-compute
      # systemctl start zun-compute

#. Enable and start zun-cni-daemon:

   .. code-block:: console

      # systemctl enable zun-cni-daemon
      # systemctl start zun-cni-daemon

#. Verify that zun-compute and zun-cni-daemon services are running:

   .. code-block:: console

      # systemctl status zun-compute
      # systemctl status zun-cni-daemon

Enable Kata Containers (Optional)
---------------------------------
By default, ``runc`` is used as the container runtime.
If you want to use Kata Containers instead, this section describes the
additional configuration steps.

.. note::

   Kata Containers requires nested virtualization or bare metal.
   See the `official document
   <https://github.com/kata-containers/documentation/tree/master/install#prerequisites>`_
   for details.

#. Enable the repository for Kata Containers:

   For Ubuntu, run:

   .. code-block:: console

      # curl -sL http://download.opensuse.org/repositories/home:/katacontainers:/releases:/$(arch):/master/xUbuntu_$(lsb_release -rs)/Release.key | apt-key add -
      # add-apt-repository "deb http://download.opensuse.org/repositories/home:/katacontainers:/releases:/$(arch):/master/xUbuntu_$(lsb_release -rs)/ /"

   For CentOS, run:

   .. code-block:: console

      # yum-config-manager --add-repo "http://download.opensuse.org/repositories/home:/katacontainers:/releases:/$(arch):/master/CentOS_7/home:katacontainers:releases:$(arch):master.repo"

#. Install Kata Containers:

   For Ubuntu, run:

   .. code-block:: console

      # apt-get update
      # apt install kata-runtime kata-proxy kata-shim

   For CentOS, run:

   .. code-block:: console

      # yum install kata-runtime kata-proxy kata-shim

#. Configure Docker to add Kata Container as runtime:

   * Edit the file ``/etc/systemd/system/docker.service.d/docker.conf``.
     Append ``--add-runtime`` option to add kata-runtime to Docker:

     .. code-block:: ini

        [Service]
        ExecStart=
        ExecStart=/usr/bin/dockerd --group zun -H tcp://compute1:2375 -H unix:///var/run/docker.sock --add-runtime kata=/usr/bin/kata-runtime

   * Restart Docker:

     .. code-block:: console

        # systemctl daemon-reload
        # systemctl restart docker

#. Configure containerd to add Kata Containers as runtime:

   * Edit the ``/etc/containerd/config.toml``.
     In the ``[plugins.cri.containerd]`` section,
     add the kata runtime configuration:

     .. code-block:: ini

        [plugins]
          ...
          [plugins.cri]
            ...
            [plugins.cri.containerd]
              ...
              [plugins.cri.containerd.runtimes.kata]
                runtime_type = "io.containerd.kata.v2"

   * Restart containerd:

     .. code-block:: console

        # systemctl restart containerd

#. Configure Zun to use Kata runtime:

   * Edit the ``/etc/zun/zun.conf``. In the ``[DEFAULT]`` section,
     configure ``container_runtime`` as kata:

     .. code-block:: ini

        [DEFAULT]
        ...
        container_runtime = kata

   * Restart zun-compute:

     .. code-block:: console

        # systemctl restart zun-compute
