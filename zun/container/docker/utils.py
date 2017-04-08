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
import six

from docker import client
from docker import errors
from docker import tls

from zun.common import exception
import zun.conf
from zun import objects

CONF = zun.conf.CONF


@contextlib.contextmanager
def docker_client():
    client_kwargs = dict()
    if not CONF.docker.api_insecure:
        client_kwargs['ca_cert'] = CONF.docker.ca_file
        client_kwargs['client_key'] = CONF.docker.key_file
        client_kwargs['client_cert'] = CONF.docker.key_file

    try:
        yield DockerHTTPClient(
            CONF.docker.api_url,
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout,
            **client_kwargs
        )
    except errors.APIError as e:
        raise exception.DockerError(error_msg=six.text_type(e))


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

    def list_containers(self):
        return self.containers(all=True, filters={'name': 'zun-'})

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

    def get_container_logs(self, docker_id, stdout, stderr, stream,
                           timestamps, tail, since):
        """Fetch the logs of a container."""
        return self.logs(docker_id, stdout, stderr, False,
                         timestamps, tail, since)
