# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

docker_group = cfg.OptGroup(name='docker',
                            title='Options for docker')

docker_opts = [
    cfg.StrOpt('docker_remote_api_version',
               default='1.26',
               help='Docker remote api version. Override it according to '
                    'specific docker api version in your environment.'),
    cfg.IntOpt('default_timeout',
               default=60,
               help='Default timeout in seconds for docker client '
                    'operations.'),
    cfg.StrOpt('api_url',
               default='unix:///var/run/docker.sock',
               help='API endpoint of docker daemon'),
    cfg.StrOpt('docker_remote_api_url',
               default='tcp://$docker_remote_api_host:$docker_remote_api_port',
               help='Remote API endpoint of docker daemon'),
    cfg.BoolOpt('api_insecure',
                default=False,
                help='If set, ignore any SSL validation issues'),
    cfg.StrOpt('ca_file',
               help='Location of CA certificates file for '
                    'securing docker api requests (tlscacert).'),
    cfg.StrOpt('cert_file',
               help='Location of TLS certificate file for '
                    'securing docker api requests (tlscert).'),
    cfg.StrOpt('key_file',
               help='Location of TLS private key file for '
                    'securing docker api requests (tlskey).'),
    cfg.StrOpt('docker_remote_api_host',
               default='$my_ip',
               help='Defines the remote api host for the docker daemon.'),
    cfg.StrOpt('docker_remote_api_port',
               default='2375',
               help='Defines the remote api port for the docker daemon.'),
    cfg.IntOpt('execute_timeout',
               default=5,
               help='Timeout in seconds for executing a command in a docker '
                    'container.'),
    cfg.StrOpt('docker_data_root',
               default='/var/lib/docker',
               help='Root directory of persistent Docker state.'),
]

ALL_OPTS = (docker_opts)


def register_opts(conf):
    conf.register_group(docker_group)
    conf.register_opts(ALL_OPTS, docker_group)


def list_opts():
    return {docker_group: ALL_OPTS}
