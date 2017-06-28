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

from oslo_config import cfg


zun_group = cfg.OptGroup(name='zun_client',
                         title='Options for the Zun client')

zun_client_opts = [
    cfg.StrOpt('region_name',
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.'),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help='Type of endpoint in Identity service catalog to use '
                    'for communication with the OpenStack service.')]


common_security_opts = [
    cfg.StrOpt('ca_file',
               help='Optional CA cert file to use in SSL connections.'),
    cfg.StrOpt('cert_file',
               help='Optional PEM-formatted certificate chain file.'),
    cfg.StrOpt('key_file',
               help='Optional PEM-formatted file that contains the '
                    'private key.'),
    cfg.BoolOpt('insecure',
                default=False,
                help="If set, then the server's certificate will not "
                     "be verified.")]

ALL_OPTS = (zun_client_opts + common_security_opts)


def register_opts(conf):
    conf.register_group(zun_group)
    conf.register_opts(zun_client_opts, group=zun_group)


def list_opts():
    return {zun_group: ALL_OPTS}
