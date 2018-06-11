=========================
Manage container security
=========================

Security groups are sets of IP filter rules that define networking access to
the container. Group rules are project specific; project members can edit the
default rules for their group and add new rule sets.

All projects have a ``default`` security group which is applied to any
container that has no other defined security group. Unless you change the
default, this security group denies all incoming traffic and allows only
outgoing traffic to your container.

Create a container with security group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When adding a new security group, you should pick a descriptive but brief name.
This name shows up in brief descriptions of the containers that use it where
the longer description field often does not. For example, seeing that a
container is using security group "http" is much easier to understand than
"bobs\_group" or "secgrp1".

#. Add the new security group, as follows:

   .. code-block:: console

      $ openstack security group create SEC_GROUP_NAME --description Description

   For example:

   .. code-block:: console

      $ openstack security group create global_http --description "Allows Web traffic anywhere on the Internet."
      +-----------------+--------------------------------------------------------------------------------------------------------------------------+
      | Field           | Value                                                                                                                    |
      +-----------------+--------------------------------------------------------------------------------------------------------------------------+
      | created_at      | 2016-11-03T13:50:53Z                                                                                                     |
      | description     | Allows Web traffic anywhere on the Internet.                                                                             |
      | headers         |                                                                                                                          |
      | id              | c0b92b20-4575-432a-b4a9-eaf2ad53f696                                                                                     |
      | name            | global_http                                                                                                              |
      | project_id      | 5669caad86a04256994cdf755df4d3c1                                                                                         |
      | project_id      | 5669caad86a04256994cdf755df4d3c1                                                                                         |
      | revision_number | 1                                                                                                                        |
      | rules           | created_at='2016-11-03T13:50:53Z', direction='egress', ethertype='IPv4', id='4d8cec94-e0ee-4c20-9f56-8fb67c21e4df',      |
      |                 | project_id='5669caad86a04256994cdf755df4d3c1', revision_number='1', updated_at='2016-11-03T13:50:53Z'                    |
      |                 | created_at='2016-11-03T13:50:53Z', direction='egress', ethertype='IPv6', id='31be2ad1-be14-4aef-9492-ecebede2cf12',      |
      |                 | project_id='5669caad86a04256994cdf755df4d3c1', revision_number='1', updated_at='2016-11-03T13:50:53Z'                    |
      | updated_at      | 2016-11-03T13:50:53Z                                                                                                     |
      +-----------------+--------------------------------------------------------------------------------------------------------------------------+

#. Add a new group rule, as follows:

   .. code-block:: console

      $ openstack security group rule create SEC_GROUP_NAME \
          --protocol PROTOCOL --dst-port FROM_PORT:TO_PORT --remote-ip CIDR

   The arguments are positional, and the ``from-port`` and ``to-port``
   arguments specify the local port range connections are allowed to access,
   not the source and destination ports of the connection. For example:

   .. code-block:: console

      $ openstack security group rule create global_http \
          --protocol tcp --dst-port 80:80 --remote-ip 0.0.0.0/0
      +-------------------+--------------------------------------+
      | Field             | Value                                |
      +-------------------+--------------------------------------+
      | created_at        | 2016-11-06T14:02:00Z                 |
      | description       |                                      |
      | direction         | ingress                              |
      | ethertype         | IPv4                                 |
      | headers           |                                      |
      | id                | 2ba06233-d5c8-43eb-93a9-8eaa94bc9eb5 |
      | port_range_max    | 80                                   |
      | port_range_min    | 80                                   |
      | project_id        | 5669caad86a04256994cdf755df4d3c1     |
      | project_id        | 5669caad86a04256994cdf755df4d3c1     |
      | protocol          | tcp                                  |
      | remote_group_id   | None                                 |
      | remote_ip_prefix  | 0.0.0.0/0                            |
      | revision_number   | 1                                    |
      | security_group_id | c0b92b20-4575-432a-b4a9-eaf2ad53f696 |
      | updated_at        | 2016-11-06T14:02:00Z                 |
      +-------------------+--------------------------------------+

#. Create a container with the new security group, as follows:

   .. code-block:: console

      $ openstack appcontainer run --security-group SEC_GROUP_NAME IMAGE

   For example:

   .. code-block:: console

      $ openstack appcontainer run --security-group global_http nginx

Find container's security groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you cannot access your application inside the container, you might want to
check the security groups of the container to ensure the rules don't block
the traffic.

#. List the containers, as follows:

   .. code-block:: console

      $ openstack appcontainer list
      +--------------------------------------+--------------------+-------+---------+------------+-----------+-------+
      | uuid                                 | name               | image | status  | task_state | addresses | ports |
      +--------------------------------------+--------------------+-------+---------+------------+-----------+-------+
      | 6595aff8-6c1c-4e64-8aad-bfd3793efa54 | delta-24-container | nginx | Running | None       | 10.5.0.14 | [80]  |
      +--------------------------------------+--------------------+-------+---------+------------+-----------+-------+

#. Find all your container's ports, as follows:

   .. code-block:: console

      $ openstack port list --fixed-ip ip-address=10.5.0.14
      +--------------------------------------+-----------------------------------------------------------------------+-------------------+--------------------------------------------------------------------------+--------+
      | ID                                   | Name                                                                  | MAC Address       | Fixed IP Addresses                                                       | Status |
      +--------------------------------------+-----------------------------------------------------------------------+-------------------+--------------------------------------------------------------------------+--------+
      | b02df384-fd58-43ee-a44a-f17be9dd4838 | 405061f9eeda5dbfa10701a72051c91a5555d19f6ef7b3081078d102fe6f60ab-port | fa:16:3e:52:3c:0c | ip_address='10.5.0.14', subnet_id='7337ad8b-7314-4a33-ba54-7362f0a7a680' | ACTIVE |
      +--------------------------------------+-----------------------------------------------------------------------+-------------------+--------------------------------------------------------------------------+--------+

#. View the details of each port to retrieve the list of security groups,
   as follows:

   .. code-block:: console

      $ openstack port show b02df384-fd58-43ee-a44a-f17be9dd4838
      +-----------------------+--------------------------------------------------------------------------+
      | Field                 | Value                                                                    |
      +-----------------------+--------------------------------------------------------------------------+
      | admin_state_up        | UP                                                                       |
      | allowed_address_pairs |                                                                          |
      | binding_host_id       | None                                                                     |
      | binding_profile       | None                                                                     |
      | binding_vif_details   | None                                                                     |
      | binding_vif_type      | None                                                                     |
      | binding_vnic_type     | normal                                                                   |
      | created_at            | 2018-05-11T21:58:42Z                                                     |
      | data_plane_status     | None                                                                     |
      | description           |                                                                          |
      | device_id             | 6595aff8-6c1c-4e64-8aad-bfd3793efa54                                     |
      | device_owner          | compute:kuryr                                                            |
      | dns_assignment        | None                                                                     |
      | dns_name              | None                                                                     |
      | extra_dhcp_opts       |                                                                          |
      | fixed_ips             | ip_address='10.5.0.14', subnet_id='7337ad8b-7314-4a33-ba54-7362f0a7a680' |
      | id                    | b02df384-fd58-43ee-a44a-f17be9dd4838                                     |
      | ip_address            | None                                                                     |
      | mac_address           | fa:16:3e:52:3c:0c                                                        |
      | name                  | 405061f9eeda5dbfa10701a72051c91a5555d19f6ef7b3081078d102fe6f60ab-port    |
      | network_id            | 695aff90-66c6-4383-b37c-7484c4046a64                                     |
      | option_name           | None                                                                     |
      | option_value          | None                                                                     |
      | port_security_enabled | True                                                                     |
      | project_id            | c907162152fe41f288912e991762b6d9                                         |
      | qos_policy_id         | None                                                                     |
      | revision_number       | 9                                                                        |
      | security_group_ids    | ba20b63e-8a61-40e4-a1a3-5798412cc36b                                     |
      | status                | ACTIVE                                                                   |
      | subnet_id             | None                                                                     |
      | tags                  | kuryr.port.existing                                                      |
      | trunk_details         | None                                                                     |
      | updated_at            | 2018-05-11T21:58:47Z                                                     |
      +-----------------------+--------------------------------------------------------------------------+

#. View the rules of security group showed up at ``security_group_ids`` field
   of the port, as follows:

   .. code-block:: console

      $ openstack security group rule list ba20b63e-8a61-40e4-a1a3-5798412cc36b
      +--------------------------------------+-------------+-----------+------------+-----------------------+
      | ID                                   | IP Protocol | IP Range  | Port Range | Remote Security Group |
      +--------------------------------------+-------------+-----------+------------+-----------------------+
      | 24ebfdb8-591c-40bb-a7d3-f5b5eadc72ca | None        | None      |            | None                  |
      | 907bf692-3dbb-4b34-ba7a-22217e6dbc4f | None        | None      |            | None                  |
      | bbcd3b46-0214-4966-8050-8b5d2f9121d1 | tcp         | 0.0.0.0/0 | 80:80      | None                  |
      +--------------------------------------+-------------+-----------+------------+-----------------------+
