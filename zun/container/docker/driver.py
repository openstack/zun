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

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common.i18n import _LI
from zun.common.i18n import _LW
from zun.common import nova
from zun.common import utils
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

    def create(self, context, container, sandbox_id, image):
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
                'name': self.get_container_name(container),
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
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
            container.save(context)
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

        config = response.get('Config')
        if config:
            # populate hostname
            container.hostname = config.get('Hostname')
            # populate ports
            ports = []
            exposed_ports = config.get('ExposedPorts')
            if exposed_ports:
                for key in exposed_ports:
                    port = key.split('/')[0]
                    ports.append(int(port))
            container.ports = ports

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
            response = docker.create_container(image, name=name,
                                               hostname=name[:63])
            sandbox_id = response['Id']
            docker.start(sandbox_id)
            return sandbox_id

    def delete_sandbox(self, context, sandbox_id):
        with docker_utils.docker_client() as docker:
            try:
                docker.remove_container(sandbox_id, force=True)
            except errors.APIError as api_error:
                if '404' in str(api_error):
                    return
                raise

    def stop_sandbox(self, context, sandbox_id):
        with docker_utils.docker_client() as docker:
            docker.stop(sandbox_id)

    def get_sandbox_id(self, container):
        if container.meta:
            return container.meta.get('sandbox_id', None)
        else:
            LOG.warning(_LW("Unexpected missing of sandbox_id"))
            return None

    def set_sandbox_id(self, container, sandbox_id):
        if container.meta is None:
            container.meta = {'sandbox_id': sandbox_id}
        else:
            container.meta['sandbox_id'] = sandbox_id

    def get_sandbox_name(self, container):
        return 'zun-sandbox-' + container.uuid

    def get_container_name(self, container):
        return 'zun-' + container.uuid

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


class NovaDockerDriver(DockerDriver):
    def create_sandbox(self, context, container, key_name=None,
                       flavor='m1.small', image='kubernetes/pause',
                       nics='auto'):
        name = self.get_sandbox_name(container)
        novaclient = nova.NovaClient(context)
        sandbox = novaclient.create_server(name=name, image=image,
                                           flavor=flavor, key_name=key_name,
                                           nics=nics)
        self._ensure_active(novaclient, sandbox)
        sandbox_id = self._find_container_by_server_name(name)
        return sandbox_id

    def _ensure_active(self, novaclient, server, timeout=300):
        '''Wait until the Nova instance to become active.'''
        def _check_active():
            return novaclient.check_active(server)

        success_msg = _LI("Created server %s successfully.") % server.id
        timeout_msg = _LE("Failed to create server %s. Timeout waiting for "
                          "server to become active.") % server.id
        utils.poll_until(_check_active,
                         sleep_time=CONF.default_sleep_time,
                         time_out=timeout or CONF.default_timeout,
                         success_msg=success_msg, timeout_msg=timeout_msg)

    def delete_sandbox(self, context, sandbox_id):
        novaclient = nova.NovaClient(context)
        server_name = self._find_server_by_container_id(sandbox_id)
        if not server_name:
            LOG.warning(_LW("Cannot find server name for sandbox %s") %
                        sandbox_id)
            return

        server_id = novaclient.delete_server(server_name)
        self._ensure_deleted(novaclient, server_id)

    def stop_sandbox(self, context, sandbox_id):
        novaclient = nova.NovaClient(context)
        server_name = self._find_server_by_container_id(sandbox_id)
        if not server_name:
            LOG.warning(_LW("Cannot find server name for sandbox %s") %
                        sandbox_id)
            return
        novaclient.stop_server(server_name)

    def _ensure_deleted(self, novaclient, server_id, timeout=300):
        '''Wait until the Nova instance to be deleted.'''
        def _check_delete_complete():
            return novaclient.check_delete_server_complete(server_id)

        success_msg = _LI("Delete server %s successfully.") % server_id
        timeout_msg = _LE("Failed to create server %s. Timeout waiting for "
                          "server to be deleted.") % server_id
        utils.poll_until(_check_delete_complete,
                         sleep_time=CONF.default_sleep_time,
                         time_out=timeout or CONF.default_timeout,
                         success_msg=success_msg, timeout_msg=timeout_msg)

    def get_addresses(self, context, container):
        novaclient = nova.NovaClient(context)
        sandbox_id = self.get_sandbox_id(container)
        if sandbox_id:
            server_name = self._find_server_by_container_id(sandbox_id)
            if server_name:
                # TODO(hongbin): Standardize the format of addresses
                return novaclient.get_addresses(server_name)
            else:
                return None
        else:
            return None

    def _find_container_by_server_name(self, name):
        with docker_utils.docker_client() as docker:
            for info in docker.list_instances(inspect=True):
                if info['Config'].get('Hostname') == name:
                    return info['Id']
            raise exception.ZunException(_(
                "Cannot find container with name %s") % name)

    def _find_server_by_container_id(self, container_id):
        with docker_utils.docker_client() as docker:
            try:
                info = docker.inspect_container(container_id)
                return info['Config'].get('Hostname')
            except errors.APIError as e:
                if e.response.status_code != 404:
                    raise
                return None
