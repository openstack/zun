#!/bin/bash -x
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# This script is executed inside gate_hook function in devstack gate.


# Keep all devstack settings here instead of project-config for easy
# maintain if we want to change devstack config settings in future.

driver=$1
db=$2

export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin kuryr-libnetwork https://git.openstack.org/openstack/kuryr-libnetwork"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin devstack-plugin-container https://git.openstack.org/openstack/devstack-plugin-container"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_USE_UWSGI=True"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"KURYR_CONFIG_DIR=/etc/kuryr-libnetwork"
export DEVSTACK_GATE_TEMPEST=1
export DEVSTACK_GATE_TEMPEST_ALL_PLUGINS=1
export DEVSTACK_GATE_TEMPEST_REGEX="zun_tempest_plugin.tests.tempest.api"

if [ "$driver" = "docker" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DRIVER=docker"
fi

if [ "$db" = "etcd" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DB_TYPE=etcd"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"KURYR_ETCD_PORT=2379"
elif [ "$db" = "sql" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DB_TYPE=sql"
fi

$BASE/new/devstack-gate/devstack-vm-gate.sh
gate_retval=$?

# Copy over docker systemd unit journals.
mkdir -p $WORKSPACE/logs
sudo journalctl -o short-precise --unit docker | sudo tee $WORKSPACE/logs/docker.txt > /dev/null

exit $gate_retval
