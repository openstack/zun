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

import six

from docker import errors
from oslo_log import log as logging

from zun.common.i18n import _LW
from zun.common.utils import check_container_id
import zun.conf
from zun.container.docker import utils as docker_utils
from zun.container import driver
from zun.objects import fields


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class DockerDriver(driver.ContainerDriver):
    '''Implementation of container drivers for Docker.'''

    def __init__(self):
        super(DockerDriver, self).__init__()

    def inspect_image(self, image, image_path=None):
        with docker_utils.docker_client() as docker:
            if image_path:
                LOG.debug('Loading local image in docker %s' % image)
                with open(image_path, 'r') as fd:
                    docker.load_image(fd.read())
            LOG.debug('Inspecting image %s' % image)
            image_dict = docker.inspect_image(image)
            return image_dict

    def images(self, repo, quiet=False):
        with docker_utils.docker_client() as docker:
            response = docker.images(repo, quiet)
            return response

    def create(self, container, sandbox_id, image):
        with docker_utils.docker_client() as docker:
            name = container.name
            if image['path']:
                LOG.debug('Loading local image %s in docker' % container.image)
                with open(image['path'], 'r') as fd:
                    docker.load_image(fd.read())
            image = container.image
            LOG.debug('Creating container with image %s name %s'
                      % (image, name))

            kwargs = {
                'hostname': container.hostname,
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
                'ports': container.ports,
                'labels': container.labels,
            }

            host_config = {}
            host_config['network_mode'] = 'container:%s' % sandbox_id
            # TODO(hongbin): Uncomment this after docker-py add support for
            # container mode for pid namespace.
            # host_config['pid_mode'] = 'container:%s' % sandbox_id
            host_config['ipc_mode'] = 'container:%s' % sandbox_id
            host_config['volumes_from'] = sandbox_id
            if container.memory is not None:
                host_config['mem_limit'] = container.memory
            if container.cpu is not None:
                host_config['cpu_quota'] = int(100000 * container.cpu)
                host_config['cpu_period'] = 100000
            kwargs['host_config'] = docker.create_host_config(**host_config)

            response = docker.create_container(image, **kwargs)
            container.container_id = response['Id']
            container.status = fields.ContainerStatus.STOPPED
            container.save()
            return container

    def delete(self, container, force):
        with docker_utils.docker_client() as docker:
            if container.container_id:
                try:
                    docker.remove_container(container.container_id,
                                            force=force)
                except errors.APIError as api_error:
                    if '404' in str(api_error):
                        return
                    raise

    def list(self):
        with docker_utils.docker_client() as docker:
            return docker.list_instances()

    def show(self, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                return container

            response = None
            try:
                response = docker.inspect_container(container.container_id)
            except errors.APIError as api_error:
                if '404' in str(api_error):
                    container.status = fields.ContainerStatus.ERROR
                    return container
                raise

            self._populate_container(container, response)
            return container

    def _populate_container(self, container, response):
        status = response.get('State')
        if status:
            if status.get('Error') is True:
                container.status = fields.ContainerStatus.ERROR
            elif status.get('Paused'):
                container.status = fields.ContainerStatus.PAUSED
            elif status.get('Running'):
                container.status = fields.ContainerStatus.RUNNING
            else:
                container.status = fields.ContainerStatus.STOPPED

    @check_container_id
    def reboot(self, container, timeout):
        with docker_utils.docker_client() as docker:
            if timeout:
                docker.restart(container.container_id,
                               timeout=int(timeout))
            else:
                docker.restart(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    @check_container_id
    def stop(self, container, timeout):
        with docker_utils.docker_client() as docker:
            if timeout:
                docker.stop(container.container_id,
                            timeout=int(timeout))
            else:
                docker.stop(container.container_id)
            container.status = fields.ContainerStatus.STOPPED
            return container

    @check_container_id
    def start(self, container):
        with docker_utils.docker_client() as docker:
            docker.start(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    @check_container_id
    def pause(self, container):
        with docker_utils.docker_client() as docker:
            docker.pause(container.container_id)
            container.status = fields.ContainerStatus.PAUSED
            return container

    @check_container_id
    def unpause(self, container):
        with docker_utils.docker_client() as docker:
            docker.unpause(container.container_id)
            container.status = fields.ContainerStatus.RUNNING
            return container

    @check_container_id
    def show_logs(self, container):
        with docker_utils.docker_client() as docker:
            return docker.get_container_logs(container.container_id)

    @check_container_id
    def execute(self, container, command):
        with docker_utils.docker_client() as docker:
            create_res = docker.exec_create(
                container.container_id, command, True, True, False)
            exec_output = docker.exec_start(create_res, False, False, False)
            return exec_output

    @check_container_id
    def kill(self, container, signal=None):
        with docker_utils.docker_client() as docker:
            if signal is None or signal == 'None':
                docker.kill(container.container_id)
            else:
                docker.kill(container.container_id, signal)
            try:
                response = docker.inspect_container(container.container_id)
            except errors.APIError as api_error:
                if '404' in str(api_error):
                    container.status = fields.ContainerStatus.ERROR
                    return container
                raise

            self._populate_container(container, response)
            return container

    def _encode_utf8(self, value):
        if six.PY2 and not isinstance(value, unicode):
            value = unicode(value)
        return value.encode('utf-8')

    def create_sandbox(self, context, container, image='kubernetes/pause'):
        with docker_utils.docker_client() as docker:
            name = self.get_sandbox_name(container)
            response = docker.create_container(image, name=name)
            sandbox_id = response['Id']
            docker.start(sandbox_id)
            return sandbox_id

    def delete_sandbox(self, context, sandbox_id):
        with docker_utils.docker_client() as docker:
            docker.remove_container(sandbox_id, force=True)

    def get_sandbox_id(self, container):
        if container.meta:
            return container.meta.get('sandbox_id', None)
        else:
            LOG.warning(_LW("Unexpected missing of sandbox_id"))
            return None

    def set_sandbox_id(self, container, id):
        if container.meta is None:
            container.meta = {'sandbox_id': id}
        else:
            container.meta['sandbox_id'] = id

    def get_sandbox_name(self, container):
        return 'sandbox-' + container.uuid

    def get_addresses(self, context, container):
        sandbox_id = self.get_sandbox_id(container)
        with docker_utils.docker_client() as docker:
            response = docker.inspect_container(sandbox_id)
            addr = response["NetworkSettings"]["IPAddress"]
            addresses = {
                'default': [
                    {
                        'addr': addr,
                    },
                ],
            }
            return addresses
