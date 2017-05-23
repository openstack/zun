==============
Tempest Plugin
==============

This directory contains Tempest tests to cover Zun project.


Tempest installation
--------------------

To install Tempest you can issue the following commands::

    $ git clone https://git.openstack.org/openstack/tempest/
    $ cd tempest/
    $ pip install .

The folder you are into now will be called ``<TEMPEST_DIR>`` from now onwards.

Please note that although it is fully working outside a virtual environment, it
is recommended to install within a `venv`.

Zun Tempest testing setup
-------------------------

Before using zun tempest plugin, you need to install zun first::

    $  pip install -e <ZUN_SRC_DIR>

To list all Zun tempest cases, go to tempest directory, then run::

    $ testr list-tests zun

Need to adopt tempest.conf, an example as follows::

    $ cat /etc/tempest/tempest.conf

    [auth]
    use_dynamic_credentials=True
    admin_username=admin
    admin_password=123
    admin_project_name=admin

    [identity]
    disable_ssl_certificate_validation=True
    uri=http://127.0.0.1:5000/v2.0/
    auth_version=v2
    region=RegionOne

    [identity-feature-enabled]
    api_v2 = true
    api_v3 = false
    trust = false

    [oslo_concurrency]
    lock_path = /tmp/

    [container_management]
    catalog_type = container

    [debug]
    trace_requests=true

To run only these tests in tempest, go to tempest directory, then run::

    $ tempest run zun

To run a single test case, go to tempest directory, then run with test case name, e.g.::

    $ tempest run --regex zun.tests.tempest.api.test_containers.TestContainer.test_create_list_delete
