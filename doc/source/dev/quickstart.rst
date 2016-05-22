.. _dev-quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for Higgins.
This assumes you are already familiar with submitting code reviews to
an OpenStack project.

.. seealso::

    http://docs.openstack.org/infra/manual/developers.html

Setup Dev Environment
=====================

Install OS-specific prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install -y libmysqlclient-dev build-essential python-dev \
                            python3.4-dev git

Install pip::

    curl -s https://bootstrap.pypa.io/get-pip.py | sudo python

Install common prerequisites::

    sudo pip install virtualenv flake8 tox testrepository git-review

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Higgins source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/higgins
    cd higgins

All unit tests should be run using tox. To run Higgins's entire test suite::

    # run all tests (unit and pep8)
    tox

To run a specific test, use a positional argument for the unit tests::

    # run a specific test for Python 2.7
    tox -epy27 -- test_conductor

You may pass options to the test programs using positional arguments::

    # run all the Python 2.7 unit tests (in parallel!)
    tox -epy27 -- --parallel

To run only the pep8/flake8 syntax and style checks::

    tox -epep8