# -*- encoding: utf-8 -*-
#
# Copyright © 2012 eNovance <licensing@enovance.com>
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

import socket

from oslo_config import cfg


service_opts = [
    cfg.HostAddressOpt('host',
                       default=socket.gethostname(),
                       sample_default='localhost',
                       help='Name of this node. This can be an '
                            'opaque identifier. It is not necessarily '
                            'a hostname, FQDN, or IP address. '
                            'However, the node name must be valid '
                            'within an AMQP key, and if using ZeroMQ, '
                            'a valid hostname, FQDN, or IP address.'),
]

periodic_opts = [
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
    cfg.IntOpt('service_down_time',
               default=180,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
]

ALL_OPTS = (service_opts + periodic_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
