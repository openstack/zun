.. _manual-install:

===============================
Manually Adding Zun to DevStack
===============================
If you are getting started with zun it is recommended you follow the
:ref:`quickstart` to get up and running with zun. This guide covers
a more in-depth process to setup zun with devstack.

This session has been tested on Ubuntu only.

Clone devstack::

    # Create a root directory for devstack if needed
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
required OpenStack services::

    cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    HOST_IP=$(ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/')
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_TOKEN=password
    SERVICE_PASSWORD=password
    ADMIN_PASSWORD=password
    enable_plugin devstack-plugin-container https://git.openstack.org/openstack/devstack-plugin-container
    enable_plugin zun https://git.openstack.org/openstack/zun
    enable_plugin kuryr-libnetwork https://git.openstack.org/openstack/kuryr-libnetwork
    END

More devstack configuration information can be found at
https://docs.openstack.org/devstack/latest/configuration.html

More neutron configuration information can be found at
https://docs.openstack.org/devstack/latest/guides/neutron.html

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
    git clone https://git.openstack.org/openstack/zun
    cd zun
    sudo pip install -c /opt/stack/requirements/upper-constraints.txt -e .

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
    iniset $ZUN_CONF keystone_authtoken auth_uri ${OS_AUTH_URL/v2.0/v3}
    iniset $ZUN_CONF keystone_authtoken auth_version v3
    iniset $ZUN_CONF keystone_authtoken auth_type password
    iniset $ZUN_CONF keystone_authtoken user_domain_id default
    iniset $ZUN_CONF keystone_authtoken project_domain_id default

Clone and install the zun client::

    cd ~
    git clone https://git.openstack.org/openstack/python-zunclient
    cd python-zunclient
    sudo pip install -c /opt/stack/requirements/upper-constraints.txt -e .

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
    openstack endpoint create --region RegionOne container public \
        http://127.0.0.1:9517/v1
    openstack endpoint create --region RegionOne container internal \
        http://127.0.0.1:9517/v1
    openstack endpoint create --region RegionOne container admin \
        http://127.0.0.1:9517/v1

Start the API service in a new screen::

    sg docker zun-api

Start the compute service in a new screen::

    sg docker zun-compute

Zun should now be up and running!
