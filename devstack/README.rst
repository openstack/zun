====================
DevStack Integration
====================

This directory contains the files necessary to integrate higgins with devstack.

Refer the quickstart guide at
https://github.com/openstack/higgins/blob/master/doc/source/dev/quickstart.rst
for more information on using devstack and higgins.

To install higgins into devstack, add the following settings to enable the
higgins plugin::

     cat > /opt/stack/devstack/local.conf << END
     [[local|localrc]]
     enable_plugin higgins https://git.openstack.org/openstack/higgins master
     END

Then run devstack normally::

    cd /opt/stack/devstack
    ./stack.sh
