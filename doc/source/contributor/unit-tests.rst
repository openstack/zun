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

==============
Run unit tests
==============

This is a guide for developers who want to run unit tests in their local
machine.

Prerequisite
============

Zun source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://opendev.org/openstack/zun
    cd zun

Install the prerequisite packages listed in the ``bindep.txt`` file.

On Debian-based distributions (e.g., Debian/Mint/Ubuntu)::

    # Ubuntu/Debian (recommend Ubuntu 16.04):
    sudo apt-get update
    sudo apt-get install python-pip
    sudo pip install tox
    tox -e bindep
    sudo apt-get install <indicated missing package names>

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS/Scientific Linux)::

    sudo yum install python-pip
    sudo pip install tox
    tox -e bindep
    sudo yum install <indicated missing package names>

On openSUSE-based distributions (SLES 12, openSUSE Leap 42.1 or Tumbleweed)::

    sudo zypper in python-pip
    sudo pip install tox
    tox -e bindep
    sudo zypper in <indicated missing package names>

Running the tests
=================

All unit tests should be run using tox. To run Zun's entire test suite::

    # run all tests (unit and pep8)
    tox

To run a specific test, use a positional argument for the unit tests::

    # run a specific test for Python 2.7
    tox -epy27 -- test_container

You may pass options to the test programs using positional arguments::

    # run all the Python 2.7 unit tests (in parallel!)
    tox -epy27 -- --parallel

To run only the pep8/flake8 syntax and style checks::

    tox -epep8
