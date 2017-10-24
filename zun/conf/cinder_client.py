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


cinder_group = cfg.OptGroup(name='cinder_client',
                            title='Options for the Cinder client')

common_security_opts = [
    cfg.StrOpt('ca_file',
               help='Optional CA cert file to use in SSL connections.'),
    cfg.BoolOpt('insecure',
                default=False,
                help="If set, then the server's certificate will not "
                     "be verified.")]

cinder_client_opts = [
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help='Type of endpoint in Identity service catalog to use '
                    'for communication with the OpenStack service.'),
    cfg.StrOpt('api_version',
               default='3',
               help='Version of Cinder API to use in cinderclient.')]


ALL_OPTS = (cinder_client_opts + common_security_opts)


def register_opts(conf):
    conf.register_group(cinder_group)
    conf.register_opts(ALL_OPTS, group=cinder_group)


def list_opts():
    return {cinder_group: ALL_OPTS}
