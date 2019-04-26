..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
      See the License for the specific language governing permissions and
      limitations under the License.

======================
 Use OSProfiler in Zun
======================

This is the demo for Zun integrating with osprofiler. `Zun
<https://wiki.openstack.org/wiki/Zun>`_ is an OpenStack container
management services, while `OSProfiler
<https://docs.openstack.org/osprofiler/latest/>`_ provides
a tiny but powerful library that is used by most OpenStack projects and
their python clients.

Install Redis database
----------------------

After osprofiler 1.4.0, user can choose mongodb or redis as the backend storage
option without using ceilometer. Here just use Redis as an example, user
can choose mongodb, elasticsearch, and `etc
<https://opendev.org/openstack/osprofiler/src/branch/master/osprofiler/drivers>`_.
Install Redis as the `centralized collector
<https://docs.openstack.org/osprofiler/latest/user/collectors.html>`_.
Redis in container is easy to launch, `choose Redis Docker
<https://hub.docker.com/_/redis/>`_ and run::

  $ docker run --name some-redis -p 6379:6379 -d redis

Now there is a redis database which has an expose port to access. OSProfiler
will send data to this key-value database.

Change the configure file
-------------------------

Change the /etc/zun/zun.conf, add the following lines, change the <ip-address>
to the real IP::

        [profiler]
        enabled = True
        trace_sqlalchemy = True
        hmac_keys = SECRET_KEY
        connection_string = redis://<ip-address>:6379/

Then restart zun-api and zun-compute (Attention, the newest version of
Zun has move zun-api service to apache2 server. You can't restart the
service just in screen. Use "systemctl restart apache2" will work).

Use below commands to get the trace information::

  $ zun --profile SECRET_KEY list

Use <TRACE-ID>, you will get a <TRACE-ID> for trace::

  $ osprofiler trace show <TRACE-ID> --connection-string=redis://<ip-address>:6379 --html


Troubleshooting
---------------

How to check whether the integration is fine:
Stop the Redis container, then run the command::

  $ zun --profile SECRET_KEY list

In the zun-api log, will see "ConnectionError: Error 111 connecting to
<ip-address>:6379. ECONNREFUSED." That means that osprofiler will write
the trace data to redis, but can't connect it. So the integration is fine.
When /etc/zun/api-paste.ini file changed (change the pipeline), you need to
re-deploy the zun service.
