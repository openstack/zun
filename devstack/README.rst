====================
DevStack Integration
====================

This directory contains the files necessary to integrate zun with devstack.

Refer the quickstart guide at
https://docs.openstack.org/zun/latest/contributor/quickstart.html
for more information on using devstack and zun.

To install zun into devstack, add the following settings to enable the
zun plugin::

     cat > /opt/stack/devstack/local.conf << END
     [[local|localrc]]
     enable_plugin zun https://git.openstack.org/openstack/zun master
     END

If you would like to install python-zunclient from git, add to local.conf::

     LIBS_FROM_GIT="python-zunclient"

Then run devstack normally::

    cd /opt/stack/devstack
    ./stack.sh
