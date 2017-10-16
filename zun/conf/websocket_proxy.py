#    Copyright 2017 Linaro Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

wsproxy_group = cfg.OptGroup("websocket_proxy",
                             title="Websocket Proxy Group",
                             help="""
Users use the websocket proxy to connect to containers, instead of
connecting to containers directly, hence protects the socket daemon.
""")

wsproxy_opts = [
    cfg.URIOpt('base_url',
               default='ws://$wsproxy_host:$wsproxy_port/',
               help="""
The URL an end user would use to connect to the ``zun-wsproxy`` service.

The ``zun-wsproxy`` service is called with this token enriched URL
and establishes the connection to the proper instance.

Related options:

* The IP address must be the same as the address to which the
  ``zun-wsproxy`` service is listening (see option ``wsproxy_host``
  in this section).
* The port must be the same as ``wsproxy_port``in this section.
    """),
    cfg.StrOpt('wsproxy_host',
               default='$my_ip',
               help="""
The IP address which is used by the ``zun-wsproxy`` service to listen
for incoming requests.

The ``zun-wsproxy`` service listens on this IP address for incoming
connection requests.

Related options:

* Ensure that this is the same IP address which is defined in the option
  ``base_url`` of this section or use ``0.0.0.0`` to listen on all addresses.
"""),
    cfg.PortOpt('wsproxy_port',
                default=6784,
                help="""
The port number which is used by the ``zun-wsproxy`` service to listen
for incoming requests.

The ``zun-wsproxy`` service listens on this port number for incoming
connection requests.

Related options:

* Ensure that this is the same port number as that defined in the option
  ``base_url`` of this section.
"""),
    cfg.ListOpt('allowed_origins',
                default=[],
                help="""
Adds list of allowed origins to the console websocket proxy to allow
connections from other origin hostnames.
Websocket proxy matches the host header with the origin header to
prevent cross-site requests. This list specifies if any there are
values other than host are allowed in the origin header.

Possible values:

* A list where each element is an allowed origin hostnames, else an empty list
"""),
]

ALL_OPTS = (wsproxy_opts)


def register_opts(conf):
    conf.register_group(wsproxy_group)
    conf.register_opts(wsproxy_opts, group=wsproxy_group)


def list_opts():
    return {wsproxy_group: ALL_OPTS}
