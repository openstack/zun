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

# Notes(eliqiao): Overwrite defaut ENABLED_SERVICES since currently higgins
# doesn't relay on any other OpenStack service yet.
OVERRIDE_ENABLED_SERVICES="dstat,key,mysql,rabbit"
export OVERRIDE_ENABLED_SERVICES

$BASE/new/devstack-gate/devstack-vm-gate.sh
