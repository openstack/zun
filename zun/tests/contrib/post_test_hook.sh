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

# This script is executed inside post_test_hook function in devstack gate.

# Sleep some time until all services are starting
sleep 5

# Check if a function already exists
function function_exists {
    declare -f -F $1 > /dev/null
}

if ! function_exists echo_summary; then
    function echo_summary {
        echo $@
    }
fi

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "Zun's post_test_hook.sh was called..."
(set -o posix; set)

# source it to make sure to get REQUIREMENTS_DIR
source $BASE/new/devstack/stackrc

constraints="-c $REQUIREMENTS_DIR/upper-constraints.txt"
sudo -H pip install $constraints -U -r requirements.txt -r test-requirements.txt

export ZUN_DIR="$BASE/new/higgins"
sudo chown -R jenkins:stack $ZUN_DIR

# Use tempest to test zun api service

# Import devstack functions 'iniset', 'iniget' and 'trueorfalse'
source $BASE/new/devstack/functions
echo "TEMPEST_SERVICES+=,zun" >> $localrc_path
pushd $BASE/new/tempest
sudo chown -R jenkins:stack $BASE/new/tempest

# Missing tempest.conf ??
# show tempest config
# cat etc/tempest.conf

# sudo -H -u jenkins tox -eall-plugin -- zun.tests.tempest.api --concurrency=1

EXIT_CODE=$?

popd


$XTRACE
exit $EXIT_CODE
