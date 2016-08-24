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
                            python3.4-dev git

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
    git clone https://git.openstack.org/openstack/higgins
    cd higgins

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

This session has only been tested on Ubuntu 14.04 (Trusty).
We recommend users to select one of it if it is possible.

Clone devstack::

    # Create a root directory for devstack if needed
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
required OpenStack services::

    cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_TOKEN=password
    SERVICE_PASSWORD=password
    ADMIN_PASSWORD=password
    # zun requires the following to be set correctly
    PUBLIC_INTERFACE=eth1
    END

**NOTE:** Update PUBLIC_INTERFACE as appropriate for your system.

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

Create a database in MySQL for zun::

    mysql -h 127.0.0.1 -u root -ppassword mysql <<EOF
    CREATE DATABASE IF NOT EXISTS zun DEFAULT CHARACTER SET utf8;
    GRANT ALL PRIVILEGES ON zun.* TO
        'root'@'%' IDENTIFIED BY 'password'
    EOF

Create the service credentials for zun::

    openstack user create --password password zun
    openstack role add --project service --user zun admin

Clone and install zun::

    cd ~
    git clone https://git.openstack.org/openstack/higgins
    cd higgins
    sudo pip install -e .

Configure zun::

    # create the zun conf directory
    ZUN_CONF_DIR=/etc/zun
    ZUN_CONF=$ZUN_CONF_DIR/zun.conf
    sudo mkdir -p $ZUN_CONF_DIR
    sudo chown -R ${USER} $ZUN_CONF_DIR

    # generate sample config file and modify it as necessary
    sudo chown -R ${USER} .
    tox -egenconfig
    sudo cp etc/zun/zun.conf.sample $ZUN_CONF_DIR/zun.conf
    sudo cp etc/zun/api-paste.ini $ZUN_CONF_DIR/api-paste.ini

    # copy policy.json
    sudo cp etc/zun/policy.json $ZUN_CONF_DIR/policy.json

    # enable debugging output
    sudo sed -i "s/#debug\s*=.*/debug=true/" $ZUN_CONF

    # set RabbitMQ userid
    sudo sed -i "s/#rabbit_userid\s*=.*/rabbit_userid=stackrabbit/" \
             $ZUN_CONF

    # set RabbitMQ password
    sudo sed -i "s/#rabbit_password\s*=.*/rabbit_password=password/" \
             $ZUN_CONF

    # set SQLAlchemy connection string to connect to MySQL
    sudo sed -i "s/#connection\s*=.*/connection=mysql:\/\/root:password@localhost\/zun/" \
             $ZUN_CONF

    # set keystone_auth
    source /opt/stack/devstack/openrc admin admin
    iniset $ZUN_CONF keystone_auth auth_type password
    iniset $ZUN_CONF keystone_auth username zun
    iniset $ZUN_CONF keystone_auth password password
    iniset $ZUN_CONF keystone_auth project_name service
    iniset $ZUN_CONF keystone_auth project_domain_id default
    iniset $ZUN_CONF keystone_auth user_domain_id default
    iniset $ZUN_CONF keystone_auth auth_url ${OS_AUTH_URL/v2.0/v3}

    # NOTE: keystone_authtoken section is deprecated and will be removed.
    iniset $ZUN_CONF keystone_authtoken username zun
    iniset $ZUN_CONF keystone_authtoken password password
    iniset $ZUN_CONF keystone_authtoken project_name service
    iniset $ZUN_CONF keystone_authtoken auth_url ${OS_AUTH_URL/v2.0/v3}
    iniset $ZUN_CONF keystone_authtoken auth_version v3
    iniset $ZUN_CONF keystone_authtoken auth_type password
    iniset $ZUN_CONF keystone_authtoken user_domain_id default
    iniset $ZUN_CONF keystone_authtoken project_domain_id default

Clone and install the zun client::

    cd ~
    git clone https://git.openstack.org/openstack/python-zunclient
    cd python-zunclient
    sudo pip install -e .

Install docker::

    curl -fsSL https://get.docker.com/ | sudo sh
    sudo usermod -a -G docker $(whoami)

Configure the database for use with zun. Please note that DB migration
does not work for SQLite backend. The SQLite database does not
have any support for the ALTER statement needed by relational schema
based migration tools. Hence DB Migration will not work for SQLite
backend::

    zun-db-manage upgrade

Configure the keystone endpoint::

    openstack service create --name=zun \
                              --description="Zun Container Service" \
                              container
    openstack endpoint create --publicurl http://127.0.0.1:9512/v1 \
                              --adminurl http://127.0.0.1:9512/v1 \
                              --internalurl http://127.0.0.1:9512/v1 \
                              --region=RegionOne \
                              container

Start the API service in a new screen::

    sg docker zun-api

Start the compute service in a new screen::

    sg docker zun-compute

Zun should now be up and running!

Using the service
=================

We will create a container that pings the address 8.8.8.8 four times::

    zun create --name test --image cirros --command "ping -c 4 8.8.8.8"
    zun start test

You should see a similar output to::

    zun list
    +--------------------------------------+------+---------+--------+-------------------+--------+
    | uuid                                 | name | status  | image  | command           | memory |
    +--------------------------------------+------+---------+--------+-------------------+--------+
    | 010fde12-bcc4-4857-94e3-e3f0e301fc7f | test | Stopped | cirros | ping -c 4 8.8.8.8 | None   |
    +--------------------------------------+------+---------+--------+-------------------+--------+

    zun logs test
    PING 8.8.8.8 (8.8.8.8): 56 data bytes
    64 bytes from 8.8.8.8: seq=0 ttl=40 time=25.513 ms
    64 bytes from 8.8.8.8: seq=1 ttl=40 time=25.348 ms
    64 bytes from 8.8.8.8: seq=2 ttl=40 time=25.226 ms
    64 bytes from 8.8.8.8: seq=3 ttl=40 time=25.275 ms

    --- 8.8.8.8 ping statistics ---
    4 packets transmitted, 4 packets received, 0% packet loss
    round-trip min/avg/max = 25.226/25.340/25.513 ms

Delete the container::

    zun delete test
