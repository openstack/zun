==============
Tempest Plugin
==============

This directory contains Tempest tests to cover Zun project.

To list all Zun tempest cases, go to tempest directory, then run::

    $ testr list-tests zun

To run only these tests in tempest, go to tempest directory, then run::

    $ ./run_tempest.sh -N -- zun

To run a single test case, go to tempest directory, then run with test case name, e.g.::

    $ ./run_tempest.sh -- -N zun.tests.tempest.api.test_basic.TestBasic.test_basic
