.. _launch-container:

Launch a container
~~~~~~~~~~~~~~~~~~

In environments that include the Container service, you can launch a
container.

#. Source the ``demo`` credentials to perform
   the following steps as a non-administrative project:

   .. code-block:: console

      $ . demo-openrc

#. Determine available networks.

   .. code-block:: console

      $ openstack network list
      +--------------------------------------+-------------+--------------------------------------+
      | ID                                   | Name        | Subnets                              |
      +--------------------------------------+-------------+--------------------------------------+
      | 4716ddfe-6e60-40e7-b2a8-42e57bf3c31c | selfservice | 2112d5eb-f9d6-45fd-906e-7cabd38b7c7c |
      | b5b6993c-ddf9-40e7-91d0-86806a42edb8 | provider    | 310911f6-acf0-4a47-824e-3032916582ff |
      +--------------------------------------+-------------+--------------------------------------+

   .. note::

      This output may differ from your environment.

#. Set the ``NET_ID`` environment variable to reflect the ID of a network.
   For example, using the selfservice network:

   .. code-block:: console

      $ export NET_ID=$(openstack network list | awk '/ selfservice / { print $2 }')

#. Run a CirrOS container on the selfservice network:

   .. code-block:: console

      $ openstack appcontainer run --name container --net network=$NET_ID cirros ping 8.8.8.8

#. After a short time, verify successful creation of the container:

   .. code-block:: console

      $ openstack appcontainer list
      +--------------------------------------+-----------+--------+---------+------------+-------------------------------------------------+-------+
      | uuid                                 | name      | image  | status  | task_state | addresses                                       | ports |
      +--------------------------------------+-----------+--------+---------+------------+-------------------------------------------------+-------+
      | 4ec10d48-1ed8-492a-be5a-402be0abc66a | container | cirros | Running | None       | 10.0.0.11, fd13:fd51:ebe8:0:f816:3eff:fe9c:7612 | []    |
      +--------------------------------------+-----------+--------+---------+------------+-------------------------------------------------+-------+

#. Access the container and verify access to the internet:

   .. code-block:: console

      $ openstack appcontainer exec --interactive container /bin/sh
      # ping -c 4 openstack.org
      # exit

#. Stop and delete the container.

   .. code-block:: console

      $ openstack appcontainer stop container
      $ openstack appcontainer delete container
