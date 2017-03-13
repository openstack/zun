.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Zun.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

.. seealso::

    http://docs.openstack.org/infra/manual/developers.html

Setup Dev Environment
=====================

Install OS-specific prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install -y libmysqlclient-dev build-essential python-dev \
                            python3.4-dev git libssl-dev libffi-dev

Install pip::

    curl -s https://bootstrap.pypa.io/get-pip.py | sudo python

Install common prerequisites::

    sudo pip install virtualenv flake8 tox testrepository git-review

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Zun source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/zun
    cd zun

All unit tests should be run using tox. To run Zun's entire test suite::

    # run all tests (unit and pep8)
    tox

To run a specific test, use a positional argument for the unit tests::

    # run a specific test for Python 2.7
    tox -epy27 -- test_conductor

You may pass options to the test programs using positional arguments::

    # run all the Python 2.7 unit tests (in parallel!)
    tox -epy27 -- --parallel

To run only the pep8/flake8 syntax and style checks::

    tox -epep8

Exercising the Services Using Devstack
======================================

This session has been tested on Ubuntu only.

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
      enable_plugin kuryr-libnetwork http://git.openstack.org/openstack/kuryr-libnetwork

      # Optional:  uncomment to enable the Zun UI plugin in Horizon
      # enable_plugin zun-ui https://git.openstack.org/openstack/zun-ui
      END

By default, devstack will enable docker driver in Zun. Alternatively, you can
enable nova-docker driver instead. If nova-docker driver is enabled, zun will
use Nova to manage `container sandboxes <https://github.com/openstack/zun/blob/master/specs/container-sandbox.rst>`_.
Simply speaking, you should choose nova-docker driver if you want to get
containers with networking provided by Neutron. Otherwise, choose docker
driver::

    $ cat >> /opt/stack/devstack/local.conf << END
      ZUN_DRIVER=nova-docker
      IP_VERSION=4
      disable_service n-net
      enable_service q-svc
      enable_service q-agt
      enable_service q-dhcp
      enable_service q-l3
      enable_service q-meta
      enable_service neutron
      END

More devstack configuration information can be found at
http://docs.openstack.org/developer/devstack/configuration.html

More neutron configuration information can be found at
http://docs.openstack.org/developer/devstack/guides/neutron.html

Run devstack::

    cd /opt/stack/devstack
    ./stack.sh

Prepare your session to be able to use the various openstack clients including
nova, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    source /opt/stack/devstack/openrc admin admin

Using the service
=================

We will create a container that pings the address 8.8.8.8 four times::

    zun create --name test --command "ping -c 4 8.8.8.8" cirros
    zun start test

You should see a similar output to::

    $ zun list
      +--------------------------------------+------+---------+--------+-------------------+--------+
      | uuid                                 | name | status  | image  | command           | memory |
      +--------------------------------------+------+---------+--------+-------------------+--------+
      | 010fde12-bcc4-4857-94e3-e3f0e301fc7f | test | Stopped | cirros | ping -c 4 8.8.8.8 | None   |
      +--------------------------------------+------+---------+--------+-------------------+--------+

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
