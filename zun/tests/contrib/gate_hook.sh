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
export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_USE_MOD_WSGI=True"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service etcd3"

if [ "$driver" = "docker" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DRIVER=docker"
elif [ "$driver" = "nova-docker" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DRIVER=nova-docker"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IP_VERSION=4"
fi

if [ "$db" = "etcd" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DB_TYPE=etcd"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"KURYR_ETCD_PORT=2379"
elif [ "$db" = "sql" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"ZUN_DB_TYPE=sql"
fi

$BASE/new/devstack-gate/devstack-vm-gate.sh
