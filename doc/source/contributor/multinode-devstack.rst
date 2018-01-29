..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===================
Multi-host Devstack
===================

This is a guide for developers who want to setup Zun in more than one hosts.

Prerequisite
============

You need to deploy Zun in a devstack environment in the first host.

Refer the ``Exercising the Services Using Devstack`` session at `Developer
Quick-Start Guide <https://docs.openstack.org/zun/latest/contributor/quickstart.html#exercising-the-services-using-devstack>`_
for details.

Enable additional zun host
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
