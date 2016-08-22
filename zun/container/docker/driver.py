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

from docker import errors
import six

from oslo_config import cfg
from oslo_log import log as logging

from zun.common import exception
from zun.common.i18n import _
from zun.container.docker import utils as docker_utils
from zun.container import driver
from zun.objects import fields


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DockerDriver(driver.ContainerDriver):
    '''Implementation of container drivers for Docker.'''

    def __init__(self):
        super(DockerDriver, self).__init__()

    def pull_image(self, image):
        with docker_utils.docker_client() as docker:
            LOG.debug('Pulling image %s' % image)
            image_repo, image_tag = docker_utils.parse_docker_image(image)
            docker.pull(image_repo, tag=image_tag)

    def create(self, container):
        with docker_utils.docker_client() as docker:
            name = container.name
            image = container.image
            LOG.debug('Creating container with image %s name %s'
                      % (image, name))
            try:
                kwargs = {'name': name,
                          'hostname': container.uuid,
                          'command': container.command,
                          'environment': container.environment}
                if docker_utils.is_docker_api_version_atleast(docker, '1.19'):
                    if container.memory is not None:
                        kwargs['host_config'] = {'mem_limit':
                                                 container.memory}
                else:
                    kwargs['mem_limit'] = container.memory

                response = docker.create_container(image, **kwargs)
                container.container_id = response['Id']
                container.status = fields.ContainerStatus.STOPPED
            except errors.APIError as e:
                container.status = fields.ContainerStatus.ERROR
                container.status_reason = six.text_type(e)
                raise
            container.save()
            return container

    def delete(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id:
                docker.remove_container(container.container_id)

    def list(self):
        with docker_utils.docker_client() as docker:
            return docker.list_instances()

    def show(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                return container

            result = None
            try:
                result = docker.inspect_container(container.container_id)
            except errors.APIError as api_error:
                if '404' in str(api_error):
                    container.status = fields.ContainerStatus.ERROR
                    return container
                raise

            status = result.get('State')
            if status:
                if status.get('Error') is True:
                    container.status = fields.ContainerStatus.ERROR
                elif status.get('Paused'):
                    container.status = fields.ContainerStatus.PAUSED
                elif status.get('Running'):
                    container.status = fields.ContainerStatus.RUNNING
                else:
                    container.status = fields.ContainerStatus.STOPPED
            return container

    def reboot(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot reboot a uncreated container.")
                raise exception.Invalid(message=msg)

            docker.restart(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    def stop(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot stop a uncreated container.")
                raise exception.Invalid(message=msg)

            docker.stop(container.container_id)
            container.status = fields.ContainerStatus.STOPPED
            return container

    def start(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot start a uncreated container.")
                raise exception.Invalid(message=msg)

            docker.start(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    def pause(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot pause a uncreated container.")
                raise exception.Invalid(message=msg)

            docker.pause(container.container_id)
            container.status = fields.ContainerStatus.PAUSED
            return container

    def unpause(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot unpause a uncreated container.")
                raise exception.Invalid(message=msg)

            docker.unpause(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    def show_logs(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot show logs of a uncreated container.")
                raise exception.Invalid(message=msg)

            return docker.get_container_logs(container.container_id)

    def execute(self, container, command):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                msg = _("Cannot execute a command in a uncreated container.")
                raise exception.Invalid(message=msg)

            if docker_utils.is_docker_library_version_atleast('1.2.0'):
                create_res = docker.exec_create(
                    container.container_id, command, True, True, False)
                exec_output = docker.exec_start(create_res, False, False,
                                                False)
            else:
                exec_output = docker.execute(container.container_id, command)
            return exec_output

    def _encode_utf8(self, value):
        if six.PY2 and not isinstance(value, unicode):
            value = unicode(value)
        return value.encode('utf-8')
