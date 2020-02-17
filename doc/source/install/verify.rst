.. _verify:

Verify operation
~~~~~~~~~~~~~~~~

Verify operation of the Container service.

.. note::

   Perform these commands on the controller node.

#. Install python-zunclient:

   .. code-block:: console

      #  pip3 install python-zunclient

#. Source the ``admin`` tenant credentials:

   .. code-block:: console

      $ . admin-openrc

#. List service components to verify successful launch and
   registration of each process:

   .. code-block:: console

      $ openstack appcontainer service list
      +----+-----------------------+-------------+-------+----------+-----------------+---------------------------+--------------------+
      | Id | Host                  | Binary      | State | Disabled | Disabled Reason | Updated At                | Availability Zone  |
      +----+-----------------------+-------------+-------+----------+-----------------+---------------------------+--------------------+
      |  1 | localhost.localdomain | zun-compute | up    | False    | None            | 2018-03-13 14:15:40+00:00 | nova               |
      +----+-----------------------+-------------+-------+----------+-----------------+---------------------------+--------------------+
