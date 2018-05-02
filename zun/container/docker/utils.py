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
import sys
import tarfile

import docker
from docker import errors
from oslo_serialization import jsonutils
from oslo_utils import encodeutils

from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
import zun.conf


CONF = zun.conf.CONF


@contextlib.contextmanager
def docker_client():
    client_kwargs = dict()
    if not CONF.docker.api_insecure:
        client_kwargs['ca_cert'] = CONF.docker.ca_file
        client_kwargs['client_key'] = CONF.docker.key_file
        client_kwargs['client_cert'] = CONF.docker.cert_file

    try:
        yield DockerHTTPClient(
            CONF.docker.api_url,
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout,
            **client_kwargs
        )
    except errors.APIError as e:
        desired_exc = exception.DockerError(error_msg=six.text_type(e))
        six.reraise(type(desired_exc), desired_exc, sys.exc_info()[2])


class DockerHTTPClient(docker.APIClient):
    def __init__(self, url=CONF.docker.api_url,
                 ver=CONF.docker.docker_remote_api_version,
                 timeout=CONF.docker.default_timeout,
                 ca_cert=None,
                 client_key=None,
                 client_cert=None):

        if ca_cert and client_key and client_cert:
            ssl_config = docker.tls.TLSConfig(
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

    def list_containers(self):
        return self.containers(all=True, filters={'name': consts.NAME_PREFIX})

    def read_tar_image(self, image):
        image_path = image['path']
        with tarfile.open(image_path, 'r') as fil:
            fest = fil.extractfile('manifest.json')
            data = fest.read()
            data = jsonutils.loads(encodeutils.safe_decode(data))
            repo_tags = data[0]['RepoTags']
            if repo_tags:
                repo, tag = repo_tags[0].split(":")
                image['repo'], image['tag'] = repo, tag
            else:
                image_uuid = data[0]['Config'].split('.')[0]
                image['repo'], image['tag'] = image_uuid, ''

    def exec_resize(self, exec_id, height=None, width=None):
        # NOTE(hongbin): This is a temporary work-around for a docker issue
        # See: https://github.com/moby/moby/issues/35561
        try:
            super(DockerHTTPClient, self).exec_resize(
                exec_id, height=height, width=width)
        except errors.APIError as e:
            if "process not found for container" in str(e):
                raise exception.Invalid(_(
                    "no such exec instance: %s") % six.text_type(e))
            raise
