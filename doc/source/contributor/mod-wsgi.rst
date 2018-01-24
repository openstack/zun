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

============================
 Installing the API via WSGI
============================

This document provides two WSGI deployments as examples: uwsgi and mod_wsgi.

.. seealso::

    https://governance.openstack.org/tc/goals/pike/deploy-api-in-wsgi.html#uwsgi-vs-mod-wsgi

Installing the API behind mod_wsgi
==================================

Zun comes with a few example files for configuring the API
service to run behind Apache with ``mod_wsgi``.

app.wsgi
========

The file ``zun/api/app.wsgi`` sets up the V2 API WSGI
application. The file is installed with the rest of the zun
application code, and should not need to be modified.

etc/apache2/zun.conf
======================

The ``etc/apache2/zun.conf`` file contains example settings that
work with a copy of zun installed via devstack.

.. literalinclude:: ../../../etc/apache2/zun.conf.template

1. On deb-based systems copy or symlink the file to
   ``/etc/apache2/sites-available``. For rpm-based systems the file will go in
   ``/etc/httpd/conf.d``.

2. Modify the ``WSGIDaemonProcess`` directive to set the ``user`` and
   ``group`` values to an appropriate user on your server. In many
   installations ``zun`` will be correct. Modify the ``WSGIScriptAlias``
   directive to set the path of the wsgi script. If you are using devstack,
   the value should be ``/opt/stack/zun/zun/api/app.wsgi``. In the
   ``ErrorLog`` and ``CustomLog`` directives, replace ``%APACHE_NAME%`` with
   ``apache2``.

3. Enable the zun site. On deb-based systems::

      $ a2ensite zun
      $ service apache2 reload

   On rpm-based systems::

      $ service httpd reload


Installing the API with uwsgi
=============================


Create zun-uwsgi.ini file::

    [uwsgi]
    http = 0.0.0.0:9517
    wsgi-file = <path_to_zun>/zun/api/app.wsgi
    plugins = python
    # This is running standalone
    master = true
    # Set die-on-term & exit-on-reload so that uwsgi shuts down
    exit-on-reload = true
    die-on-term = true
    # uwsgi recommends this to prevent thundering herd on accept.
    thunder-lock = true
    # Override the default size for headers from the 4k default. (mainly for keystone token)
    buffer-size = 65535
    enable-threads = true
    # Set the number of threads usually with the returns of command nproc
    threads = 8
    # Make sure the client doesn't try to re-use the connection.
    add-header = Connection: close
    # Set uid and gip to a appropriate user on your server. In many
    # installations ``zun`` will be correct.
    uid = zun
    gid = zun

Then start the uwsgi server::

    uwsgi ./zun-uwsgi.ini

Or start in background with::

    uwsgi -d ./zun-uwsgi.ini
