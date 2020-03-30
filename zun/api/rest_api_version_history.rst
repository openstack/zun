REST API Version History
========================

This documents the changes made to the REST API with every
microversion change. The description for each version should be a
verbose one which has enough information to be suitable for use in
user documentation.

1.1
---

  This is the initial version of the v1.1 API which supports
  microversions. The v1.1 API is from the REST API users's point of
  view exactly the same as v1.0 except with strong input validation.

  A user can specify a header in the API request::

    OpenStack-API-Version: <version>

  where ``<version>`` is any valid api version for this API.

  If no version is specified then the API will behave as if a version
  request of v1.1 was requested.

1.2
---

  Add a new attribute 'nets' to the request to create a container.
  Users can use this attribute to specify one or multiple networks for
  the container. Each network could specify the neutron network, neutron
  port, or a v4/v6 IP address. For examples::

    [{'port': '1234567'}]
    [{'v4-fixed-ip': '127.0.0.1'}]
    [{'network': 'test'}]
    [{'network': 'test2'}]
    [{'v6-fixed-ip': '2f:33:45'}]

1.3
---

  Add 'auto_remove' field for creating a container.
  With this field, the container will be automatically removed if it exists.
  The new one will be created instead.

1.4
---

  Add host list api.
  Users can use this api to list all the zun compute hosts.
  Add get host api
  Users can use this api to get details of a zun compute host.

1.5
---

  Add a new attribute 'runtime' to the request to create a container.
  Users can use this attribute to choose runtime for their containers.
  The specified runtime should be configured by admin to run with Zun.
  The default runtime for Zun is runc.

1.6
---

  Add detach a network from a container api.
  Users can use this api to detach a neutron network from a container.

1.7
---

  Disallow non-admin users to force delete containers
  Only Admin User can use "delete --force" to force delete a container.

1.8
---

  Add attach a network to a container.
  Users can use this api to attach a neutron network to a container.

1.9
---

  Add a new attribute 'hostname' to the request to create a container.
  Users can use this attribute to specify container's hostname.

1.10
----

  Make container delete API async. Delete operation for a container
  can take long time, so making it async to improve user experience.

1.11
----

  Add a new attribute 'mounts' to the request to create a container.
  Users can use this attribute to specify one or multiple mounts for
  the container. Each mount could specify the source and destination.
  The source is the Cinder volume id or name, and the destination is
  the path where the file or directory will be mounted in the container.
  For examples:

    [{'source': 'my-vol', 'destination': '/data'}]

1.12
----

  Add a new attribute 'stop' to the request to delete containers.
  Users can use this attribute to stop and delete the container without
  using the --force option.

1.13
----

  Add a new api for a list of networks on a container.
  Users can use this api to list up neutron network on a container.

1.14
----

  Remove the container rename endpoint (POST /containers/<container>/rename).
  The equivalent functionality is re-introduced by the patch endpoint
  (PATCH /containers/<container>). To rename a container, users can send
  a request to the endpoint with the data in the following form:

    {'name': '<new-name>'}

1.15
----

  Remove the APIs for adding/removing security group to/from a container.
  These APIs are removed because they are proxy APIs to Neutron.

1.16
----

  Modify restart_policy to capsule spec content to align with Kubernetes.

1.17
----

  Add parameter ``port`` to the network_detach API. This allow users to
  detach a container from a neutron port.

1.18
----

  Modify the response of network_list
  (GET /v1/containers/{container_ident}/network_list) API. The normal response
  will be something like::

    {
        "networks": [
            {
                "port_id": "5be06e49-70dc-4984-94a2-1b946bb136fb",
                "net_id": "7e6b5e1b-9b44-4f55-b4e3-16a1ead98161",
                "fixed_ips" [
                    "ip_address": "30.30.30.10",
                    "version": 4,
                    "subnet_id": "ae8d7cce-859e-432f-8a33-d7d8834ccd14"
                ]
            }
        ]
    }

1.19
----

  Introduce an API endpoint for resizing a container, such as changing the
  CPU or memory of the container.

1.20
----

  Convert type of 'command' from string to list

1.21
----

  Support privileged container

1.22
----

  Add healthcheck to container create

1.23
----

  Add support for file injection when creating a container.
  The content of the file is sent to Zun server via parameter 'mounts'.

1.24
----

  Add a parameter 'exposed_ports' to the request of creating a container.
  This parameter is of the following form:

    "exposed_ports": { "<port>/<protocol>: {}" }

  where 'port' is the container's port and 'protocol' is either 'tcp' or 'udp'.
  If this parameter is specified, Zun will create a security group and open
  the exposed port. This parameter cannot be used together with the
  'security_groups' parameter because Zun will manage the security groups of
  the container.

1.25
----

  The get_archive endpoint returns a encoded archived file data by using
  Base64 algorithm.
  The put_archive endpoint take a Base64-encoded archived file data as input.

1.26
----

  Introduce Quota support API

1.27
----

  Introduce API for deleting network. By default, this is an admin API.

1.28
----

  Add a new attribute 'cpu_policy'.
  Users can use this attribute to determine which CPU policy the container uses.

1.29
----

  Add a new attribute 'enable_cpu_pinning' to 'host' resource.

1.30
----

  Introduce API endpoint for create/read/update/delete private registry.

1.31
----

  Add 'registry_id' to container resource.
  This attribute indicate the registry from which the container pulls images.

1.32
----

  Make capsule deletion asynchronized.
  API request to delete a capsule will return without waiting for the
  capsule to be deleted.

1.33
----

  Add 'finish_time' to container action resource.
  If the action is finished, 'finish_time' shows the finish time.
  Otherwise, this field will be None.

1.34
----

  Add 'init_containers' to capsule.
  This field contains a list of init_container information.

1.35
----

  Support processing 'ports' field in capsule's container.
  Users can leverage this field to open ports of a container.
  For example::

    spec:
      containers:
      - image: "nginx"
        ports:
        - containerPort: 80
          protocol: TCP

1.36
----

  Add 'tty' to container.
  This field indicate if the container should allocate a TTY for itself.

1.37
----

  Add 'tty' and 'stdin' to capsule.
  Containers in capsule can specify these two fields.

1.38
----

  Add 'annotations' to capsule.
  This field stores metadata of the capsule in key-value format.

1.39
----

  Add 'host' parameter on POST /v1/containers.
  This field is used to request a host to run the container.

1.40
----

  Add 'entrypoint' parameter on POST /v1/containers.
  This field is used to overwrite the default ENTRYPOINT of the image.
