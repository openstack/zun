=======================
Keep Containers Alive
=======================
As we know, the Docker daemon shuts down all running containers
during daemon downtime. Starting with Docker Engine 1.12, users can
configure the daemon so that containers remain running when the
docker service becomes unavailable. This functionality is called
live restore.  You can read more about Live Restore
`here <https://docs.docker.com/config/containers/live-restore>`_.

Installation with DevStack
==========================
It is possible to keep containers alive. Follow the
:doc:`/contributor/quickstart` to download DevStack, Zun code and copy the
local.conf file. Now perform the following steps to install Zun with DevStack::

    cd /opt/stack/devstack
    echo "ENABLE_LIVE_RESTORE=true" >> local.conf
    ./stack.sh

Verify the installation by::

    $ sudo docker info | grep "Live Restore"
    Live Restore Enabled: true
