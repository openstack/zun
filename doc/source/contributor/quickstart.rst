.. _quickstart:

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
    $ sudo mkdir -p /opt/stack
    $ sudo chown $USER /opt/stack

    $ git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
required OpenStack services::

    $ HOST_IP=<your ip>
    $ git clone https://git.openstack.org/openstack/zun /opt/stack/zun
    $ cat /opt/stack/zun/devstack/local.conf.sample \
        | sed "s/HOST_IP=.*/HOST_IP=$HOST_IP/" \
        > /opt/stack/devstack/local.conf

More devstack configuration information can be found at `Devstack Configuration
<https://docs.openstack.org/devstack/latest/configuration.html>`_

More neutron configuration information can be found at `Devstack Neutron
Configuration <https://docs.openstack.org/devstack/latest/guides/neutron.html>`_

Run devstack::

    $ cd /opt/stack/devstack
    $ ./stack.sh

Prepare your session to be able to use the various openstack clients including
nova, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    $ source /opt/stack/devstack/openrc admin admin

Using the service
=================

We will create and run a container that pings the address 8.8.8.8 four times::

    $ zun run --name test cirros ping -c 4 8.8.8.8

Above command will use the Docker image ``cirros`` from DockerHub which is a
public image repository. Alternatively, you can use Docker image from Glance
which serves as a private image repository::

    $ docker pull cirros
    $ docker save cirros | openstack image create cirros --public --container-format docker --disk-format raw
    $ zun run --image-driver glance cirros ping -c 4 8.8.8.8

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

Enable the second zun host
==========================

Refer to the `Multi-Node lab
<https://docs.openstack.org/devstack/latest/guides/multinode-lab.html>`__
for more information.

On the second host, clone devstack::

    # Create a root directory for devstack if needed
    $ sudo mkdir -p /opt/stack
    $ sudo chown $USER /opt/stack

    $ git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

The second host will only need zun-compute service along with kuryr-libnetwork
support. You also need to tell devstack where the SERVICE_HOST is::

    $ SERVICE_HOST=<controller's ip>
    $ HOST_IP=<your ip>
    $ git clone https://git.openstack.org/openstack/zun /opt/stack/zun
    $ cat /opt/stack/zun/devstack/local.conf.subnode.sample \
        | sed "s/HOST_IP=.*/HOST_IP=$HOST_IP/" \
        | sed "s/SERVICE_HOST=.*/SERVICE_HOST=$SERVICE_HOST/" \
        > /opt/stack/devstack/local.conf

.. note::

    In multi-node scenario, kuryr-libnetwork config `capability_scope`
    **must be** global (By default it is local), change in file
    /etc/kuryr/kuryr.conf (all nodes): capability_scope = global

Run devstack::

    $ cd /opt/stack/devstack
    $ ./stack.sh

On the controller host, you can see 2 zun-compute hosts available::

    $ zun service-list
    +----+-------------+-------------+-------+----------+-----------------+---------------------------+---------------------------+
    | Id | Host        | Binary      | State | Disabled | Disabled Reason | Created At                | Updated At                |
    +----+-------------+-------------+-------+----------+-----------------+---------------------------+---------------------------+
    | 1  | zun-hosts-1 | zun-compute | up    | False    | None            | 2017-05-18 07:06:45+00:00 | 2017-05-19 03:20:55+00:00 |
    | 2  | zun-hosts-2 | zun-compute | up    | False    | None            | 2017-05-18 07:09:44+00:00 | 2017-05-19 03:21:10+00:00 |
    +----+-------------+-------------+-------+----------+-----------------+---------------------------+---------------------------+
