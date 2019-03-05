..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=========================
Run tempest tests locally
=========================

This is a guide for developers who want to run tempest tests in their local
machine.

Zun contains a suite of tempest tests in the zun/tests/tempest directory.
Tempest tests are primary for testing integration between Zun and its
depending software stack (i.e. Docker, other OpenStack services). Any proposed
code change will be automatically rejected by the gate if the change causes
tempest test failures. If this happens, contributors are suggested to refer
this document to re-run the tests locally and perform any necessary
trouble-shooting.

Prerequisite
============

You need to deploy Zun in a devstack environment.

Refer the ``Exercising the Services Using Devstack`` session at `Developer
Quick-Start Guide <https://docs.openstack.org/zun/latest/contributor/quickstart.html#exercising-the-services-using-devstack>`_
for details.

Run the test
============

Edit ``/opt/stack/tempest/etc/tempest.conf``:

   * Add the ``[container_service]`` section,
     configure ``min_microversion`` and ``max_microversion``:

     .. code-block:: ini

        [container_service]
        min_microversion=1.26
        max_microversion=1.26

   .. note::

      You might need to modify the min/max microversion based on your
      test environment.

Navigate to tempest directory::

    cd /opt/stack/tempest

Run this command::

    tempest run --regex zun_tempest_plugin.tests.tempest.api

To run a single test case, run with the test case name, for example::

    tempest run --regex zun_tempest_plugin.tests.tempest.api.test_containers.TestContainer.test_list_containers
