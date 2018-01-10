Contributing Documentation to Zun
=================================

Zun's documentation has been moved from the openstack-manuals repository
to the ``docs`` directory in the Zun repository.  This makes it even more
important that Zun add and maintain good documentation.


This page provides guidance on how to provide documentation for those
who may not have previously been active writing documentation for
OpenStack.

Using RST
---------

OpenStack documentation uses reStructuredText to write documentation.
The files end with a ``.rst`` extension.  The ``.rst`` files are then
processed by Sphinx to build HTML based on the RST files.

.. note::
   Files that are to be included using the ``.. include::`` directive in an
   RST file should use the ``.inc`` extension.  If you instead use the ``.rst``
   this will result in the RST file being processed twice during the build and
   cause Sphinx to generate a warning during the build.

reStructuredText is a powerful language for generating web pages.  The
documentation team has put together an `RST conventions`_ page with information
and links related to RST.

.. _RST conventions: https://docs.openstack.org/contributor-guide/rst-conv.html

Building Zun's Documentation
----------------------------

To build documentation the following command should be used:

.. code-block:: console

   tox -e docs,pep8

When building documentation it is important to also run pep8 as it is easy
to introduce pep8 failures when adding documentation.  Currently, we do not
have the build configured to treat warnings as errors, so it is also important
to check the build output to ensure that no warnings are produced by Sphinx.

.. note::

   Many Sphinx warnings result in improperly formatted pages being generated.

During the documentation build a number of things happen:

   * All of the RST files under ``doc/source`` are processed and built.

      * The openstackdocs theme is applied to all of the files so that they
        will look consistent with all the other OpenStack documentation.
      * The resulting HTML is put into ``doc/build/html``.

   * Sample files like zun.conf.sample are generated and put into
     ``doc/soure/_static``.

After the build completes the results may be accessed via a web browser in
the ``doc/build/html`` directory structure.

Review and Release Process
--------------------------
Documentation changes go through the same review process as all other changes.

.. note::

   Reviewers can see the resulting web page output by clicking on
   ``gate-zun-docs-ubuntu-xenial``!

Once a patch is approved it is immediately released to the docs.openstack.org
website and can be seen under Zun's Documentation Page at
https://docs.openstack.org/zun/latest .  When a new release is cut a
snapshot of that documentation will be kept at
https://docs.openstack.org/zun/<release> .  Changes from master can be
backported to previous branches if necessary.


Doc Directory Structure
-----------------------
The main location for Zun's documentation is the ``doc/source`` directory.
The top level index file that is seen at
`https://docs.openstack.org/zun/latest`_ resides here as well as the
``conf.py`` file which is used to set a number of parameters for the build
of OpenStack's documentation.

Each of the directories under source are for specific kinds of documentation
as is documented in the ``README`` in each directory:

.. toctree::
   :maxdepth: 1

   ../admin/README
   ../cli/README
   ../configuration/README
   ../contributor/README
   ../install/README

.. _https://docs.openstack.org/zun/latest: https://docs.openstack.org/zun/latest
