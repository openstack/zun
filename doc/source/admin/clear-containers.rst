=======================
Clear Containers in Zun
=======================

Zun now supports running Clear Containers with regular Docker containers.
Clear containers run containers as very lightweight virtual machines
which boot up really fast and has low memory footprints. It provides
security to the containers with an isolated environment. You can read
more about Clear Containers `here <https://github.com/clearcontainers/runtime/wiki>`_.

Installation with DevStack
==========================
It is possible to run Clear Containers with Zun. Follow the
:doc:`/contributor/quickstart` to download DevStack, Zun code and copy the
local.conf file. Now perform the following steps to install Clear Containers
with DevStack::

    cd /opt/stack/devstack
    echo "ENABLE_CLEAR_CONTAINER=true" >> local.conf
    ./stack.sh

Verify the installation by::

    $ sudo docker info | grep Runtimes
    Runtimes: cor runc

Using Clear Containers with Zun
===============================
To create Clear Containers with Zun, specify the `--runtime` option::

    zun run --name clear-container --runtime cor cirros ping -c 4 8.8.8.8

.. note::

    Clear Containers support in Zun is not production ready. It is recommended
    not to running Clear Containers and runc containers on the same host.
