.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Zun.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

.. seealso::

    https://docs.openstack.org/infra/manual/developers.html

Exercising the Services Using Devstack
======================================

This session has been tested on Ubuntu 16.04 (Xenial) only.

Clone devstack::

    # Create a root directory for devstack if needed
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
required OpenStack services::

    $ cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    HOST_IP=$(ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/')
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_TOKEN=password
    SERVICE_PASSWORD=password
    ADMIN_PASSWORD=password
    enable_plugin zun https://git.openstack.org/openstack/zun
    enable_plugin kuryr-libnetwork https://git.openstack.org/openstack/kuryr-libnetwork

    # Optional:  uncomment to enable the Zun UI plugin in Horizon
    # enable_plugin zun-ui https://git.openstack.org/openstack/zun-ui
    END

More devstack configuration information can be found at
https://docs.openstack.org/developer/devstack/configuration.html

More neutron configuration information can be found at
https://docs.openstack.org/developer/devstack/guides/neutron.html

Run devstack::

    cd /opt/stack/devstack
    ./stack.sh

Prepare your session to be able to use the various openstack clients including
nova, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    source /opt/stack/devstack/openrc admin admin

Using the service
=================

We will create and run a container that pings the address 8.8.8.8 four times::

    $ zun run --name test cirros ping -c 4 8.8.8.8

You should see a similar output to::

    $ zun list
      +--------------------------------------+------+--------+---------+------------+------------+-------+
      | uuid                                 | name | image  | status  | task_state | addresses  | ports |
      +--------------------------------------+------+--------+---------+------------+------------+-------+
      | 46dd001b-7474-412c-a0f4-7adc047aaedf | test | cirros | Stopped | None       | 172.17.0.2 | []    |
      +--------------------------------------+------+--------+---------+------------+------------+-------+

    $ zun logs test
      PING 8.8.8.8 (8.8.8.8): 56 data bytes
      64 bytes from 8.8.8.8: seq=0 ttl=40 time=25.513 ms
      64 bytes from 8.8.8.8: seq=1 ttl=40 time=25.348 ms
      64 bytes from 8.8.8.8: seq=2 ttl=40 time=25.226 ms
      64 bytes from 8.8.8.8: seq=3 ttl=40 time=25.275 ms

      --- 8.8.8.8 ping statistics ---
      4 packets transmitted, 4 packets received, 0% packet loss
      round-trip min/avg/max = 25.226/25.340/25.513 ms

Delete the container::

    $ zun delete test
