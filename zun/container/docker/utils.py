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
import contextlib

import docker
from docker import client
from docker import tls
from docker.utils import utils
from oslo_config import cfg

from zun import objects


docker_opts = [
    cfg.StrOpt('docker_remote_api_version',
               default='1.20',
               help='Docker remote api version. Override it according to '
                    'specific docker api version in your environment.'),
    cfg.IntOpt('default_timeout',
               default=60,
               help='Default timeout in seconds for docker client '
                    'operations.'),
    cfg.StrOpt('api_url',
               default='unix:///var/run/docker.sock',
               help='API endpoint of docker daemon'),
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
]

CONF = cfg.CONF
CONF.register_opts(docker_opts, 'docker')


def parse_docker_image(image):
    image_parts = image.split(':', 1)

    image_repo = image_parts[0]
    image_tag = None

    if len(image_parts) > 1:
        image_tag = image_parts[1]

    return image_repo, image_tag


def is_docker_library_version_atleast(version):
    if utils.compare_version(docker.version, version) <= 0:
        return True
    return False


def is_docker_api_version_atleast(docker, version):
    if utils.compare_version(docker.version()['ApiVersion'], version) <= 0:
        return True
    return False


@contextlib.contextmanager
def docker_client():
    client_kwargs = dict()
    if not CONF.docker.api_insecure:
        client_kwargs['ca_cert'] = CONF.docker.ca_file
        client_kwargs['client_key'] = CONF.docker.key_file
        client_kwargs['client_cert'] = CONF.docker.key_file

    yield DockerHTTPClient(
        CONF.docker.api_url,
        CONF.docker.docker_remote_api_version,
        CONF.docker.default_timeout,
        **client_kwargs
    )


class DockerHTTPClient(client.Client):
    def __init__(self, url=CONF.docker.api_url,
                 ver=CONF.docker.docker_remote_api_version,
                 timeout=CONF.docker.default_timeout,
                 ca_cert=None,
                 client_key=None,
                 client_cert=None):

        if ca_cert and client_key and client_cert:
            ssl_config = tls.TLSConfig(
                client_cert=(client_cert, client_key),
                verify=ca_cert,
                assert_hostname=False,
            )
        else:
            ssl_config = False

        super(DockerHTTPClient, self).__init__(
            base_url=url,
            version=ver,
            timeout=timeout,
            tls=ssl_config
        )

    def list_instances(self, inspect=False):
        """List all containers."""
        res = []
        for container in self.containers(all=True):
            info = self.inspect_container(container['Id'])
            if not info:
                continue
            if inspect:
                res.append(info)
            else:
                res.append(info['Config'].get('Hostname'))
        return res

    def pause(self, container):
        """Pause a running container."""
        if isinstance(container, objects.Container):
            container = container.container_id
        super(DockerHTTPClient, self).pause(container)

    def unpause(self, container):
        """Unpause a paused container."""
        if isinstance(container, objects.Container):
            container = container.container_id
        super(DockerHTTPClient, self).unpause(container)

    def get_container_logs(self, docker_id):
        """Fetch the logs of a container."""
        return self.logs(docker_id)
