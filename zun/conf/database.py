# Copyright 2015 NEC Corporation.  All rights reserved.
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

from oslo_config import cfg


db_opts = [
    # TODO(yuywz): Change to etcd after all etcd db driver code is landed
    cfg.StrOpt('db_type',
               default='sql',
               help='Defines which db type to use for storing container. '
                    'Possible Values: sql, etcd')
]

sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]

etcd_opts = [
    cfg.HostAddressOpt('etcd_host',
                       default='127.0.0.1',
                       help="Host IP address on which etcd service "
                            "running."),
    cfg.PortOpt('etcd_port',
                default=2379,
                help="Port on which etcd listen client request.")
]

etcd_group = cfg.OptGroup(name='etcd', title='Options for etcd connection')

ALL_OPTS = (db_opts + sql_opts + etcd_opts)


def register_opts(conf):
    conf.register_opts(db_opts)
    conf.register_opts(sql_opts, 'database')
    conf.register_group(etcd_group)
    conf.register_opts(etcd_opts, etcd_group)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
