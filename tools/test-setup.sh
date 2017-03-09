#!/usr/bin/env bash

# Borrowed from mysql-prep in openstack-infra/project-config/macros.yaml
DB_ROOT_PW=insecure_slave
DB_USER=openstack_citest
DB_PW=openstack_citest
sudo -H mysqladmin -u root password $DB_ROOT_PW
# note; we remove anonymous users first
sudo -H mysql -u root -p$DB_ROOT_PW -h localhost -e "
DELETE FROM mysql.user WHERE User='';
FLUSH PRIVILEGES;
GRANT ALL PRIVILEGES ON *.*
TO '$DB_USER'@'%' identified by '$DB_PW' WITH GRANT OPTION;"
