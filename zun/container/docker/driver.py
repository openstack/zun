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

import datetime
import six

from docker import errors
from oslo_log import log as logging
from oslo_utils import timeutils

from zun.common import exception
from zun.common.i18n import _
from zun.common import nova
from zun.common import utils
from zun.common.utils import check_container_id
import zun.conf
from zun.container.docker import utils as docker_utils
from zun.container import driver
from zun.objects import fields


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
ATTACH_FLAG = "/attach/ws?logs=0&stream=1&stdin=1&stdout=1&stderr=1"


class DockerDriver(driver.ContainerDriver):
    '''Implementation of container drivers for Docker.'''

    def __init__(self):
        super(DockerDriver, self).__init__()

    def load_image(self, image, image_path=None):
        with docker_utils.docker_client() as docker:
            if image_path:
                with open(image_path, 'rb') as fd:
                    LOG.debug('Loading local image %s into docker', image_path)
                    docker.load_image(fd)

    def inspect_image(self, image):
        with docker_utils.docker_client() as docker:
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
            image = container.image
            LOG.debug('Creating container with image %s name %s'
                      % (image, name))

            kwargs = {
                'name': self.get_container_name(container),
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
                'labels': container.labels,
                'tty': container.tty,
                'stdin_open': container.stdin_open,
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
            if container.restart_policy is not None:
                count = int(container.restart_policy['MaximumRetryCount'])
                name = container.restart_policy['Name']
                host_config['restart_policy'] = {'Name': name,
                                                 'MaximumRetryCount': count}
            kwargs['host_config'] = docker.create_host_config(**host_config)

            response = docker.create_container(image, **kwargs)
            container.container_id = response['Id']
            container.status = fields.ContainerStatus.CREATED
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
            return [container for container in docker.list_containers()
                    if 'zun-sandbox-' not in container['Names'][0]]

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

    def format_status_detail(self, status_time):
        try:
            st = datetime.datetime.strptime((status_time[:19]),
                                            '%Y-%m-%dT%H:%M:%S')
        except ValueError as e:
            LOG.exception("Error on parse {} : {}".format(status_time, e))
            return

        if st == datetime.datetime(1, 1, 1):
            # return empty string if the time is January 1, year 1, 00:00:00
            return ""

        delta = timeutils.utcnow() - st
        time_dict = {}
        time_dict['days'] = delta.days
        time_dict['hours'] = delta.seconds//3600
        time_dict['minutes'] = (delta.seconds % 3600)//60
        time_dict['seconds'] = delta.seconds
        if time_dict['days']:
            return '{} days'.format(time_dict['days'])
        if time_dict['hours']:
            return '{} hours'.format(time_dict['hours'])
        if time_dict['minutes']:
            return '{} mins'.format(time_dict['minutes'])
        if time_dict['seconds']:
            return '{} seconds'.format(time_dict['seconds'])
        return

    def _populate_container(self, container, response):
        status = response.get('State')
        if status:
            status_detail = ''
            if status.get('Error') is True:
                container.status = fields.ContainerStatus.ERROR
                status_detail = self.format_status_detail(
                    status.get('FinishedAt'))
                container.status_detail = "Exited({}) {} ago " \
                    "(error)".format(status.get('ExitCode'), status_detail)
            elif status.get('Paused'):
                container.status = fields.ContainerStatus.PAUSED
                status_detail = self.format_status_detail(
                    status.get('StartedAt'))
                container.status_detail = "Up {} (paused)".format(
                    status_detail)
            elif status.get('Running'):
                container.status = fields.ContainerStatus.RUNNING
                status_detail = self.format_status_detail(
                    status.get('StartedAt'))
                container.status_detail = "Up {}".format(
                    status_detail)
            else:
                started_at = self.format_status_detail(status.get('StartedAt'))
                finished_at = self.format_status_detail(
                    status.get('FinishedAt'))
                if started_at == "":
                    container.status = fields.ContainerStatus.CREATED
                    container.status_detail = "Created"
                elif finished_at == "":
                    container.status = fields.ContainerStatus.UNKNOWN
                    container.status_detail = ""
                else:
                    container.status = fields.ContainerStatus.STOPPED
                    container.status_detail = "Exited({}) {} ago ".format(
                        status.get('ExitCode'), finished_at)
            if status_detail is None:
                container.status_detail = None

        config = response.get('Config')
        if config:
            self._populate_hostname_and_ports(container, config)

    def _populate_hostname_and_ports(self, container, config):
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
    def show_logs(self, container, stdout=True, stderr=True,
                  timestamps=False, tail='all', since=None):
        with docker_utils.docker_client() as docker:
            try:
                tail = int(tail)
            except ValueError:
                tail = 'all'

            if since is None or since == 'None':
                return docker.get_container_logs(container.container_id,
                                                 stdout, stderr, False,
                                                 timestamps, tail, None)
            else:
                try:
                    since = int(since)
                except ValueError:
                    try:
                        since = \
                            datetime.datetime.strptime(since,
                                                       '%Y-%m-%d %H:%M:%S,%f')
                    except Exception:
                        raise
                return docker.get_container_logs(container.container_id,
                                                 stdout, stderr, False,
                                                 timestamps, tail, since)

    @check_container_id
    def execute_create(self, container, command, interactive=False):
        stdin = True if interactive else False
        tty = True if interactive else False
        with docker_utils.docker_client() as docker:
            create_res = docker.exec_create(
                container.container_id, command, stdin=stdin, tty=tty)
            exec_id = create_res['Id']
            return exec_id

    def execute_run(self, exec_id):
        with docker_utils.docker_client() as docker:
            output = docker.exec_start(exec_id, False, False, False)
            inspect_res = docker.exec_inspect(exec_id)
            return {"output": output, "exit_code": inspect_res['ExitCode']}

    def execute_resize(self, exec_id, height, width):
        height = int(height)
        width = int(width)
        with docker_utils.docker_client() as docker:
            try:
                docker.exec_resize(exec_id, height=height, width=width)
            except errors.APIError as api_error:
                if '404' in str(api_error):
                    raise exception.Invalid(_(
                        "no such exec instance: %s") % str(api_error))
                raise

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

    @check_container_id
    def update(self, container):
        patch = container.obj_get_changes()

        args = {}
        memory = patch.get('memory')
        if memory is not None:
            args['mem_limit'] = memory
        cpu = patch.get('cpu')
        if cpu is not None:
            args['cpu_quota'] = int(100000 * cpu)
            args['cpu_period'] = 100000

        with docker_utils.docker_client() as docker:
            try:
                resp = docker.update_container(container.container_id, **args)
                return resp
            except errors.APIError:
                raise

    @check_container_id
    def get_websocket_url(self, container):
        version = CONF.docker.docker_remote_api_version
        remote_api_port = CONF.docker.docker_remote_api_port
        url = "ws://" + container.host + ":" + remote_api_port + \
              "/v" + version + "/containers/" + container.container_id \
              + ATTACH_FLAG
        return url

    @check_container_id
    def resize(self, container, height, width):
        with docker_utils.docker_client() as docker:
            height = int(height)
            width = int(width)
            docker.resize(container.container_id, height, width)
            return container

    @check_container_id
    def top(self, container, ps_args=None):
        with docker_utils.docker_client() as docker:
            try:
                if ps_args is None or ps_args == 'None':
                    return docker.top(container.container_id)
                else:
                    return docker.top(container.container_id, ps_args)
            except errors.APIError:
                raise

    @check_container_id
    def get_archive(self, container, path):
        with docker_utils.docker_client() as docker:
            try:
                stream, stat = docker.get_archive(container.container_id, path)
                filedata = stream.read()
                return filedata, stat
            except errors.APIError:
                raise

    @check_container_id
    def put_archive(self, container, path, data):
        with docker_utils.docker_client() as docker:
            try:
                docker.put_archive(container.container_id, path, data)
            except errors.APIError:
                raise

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
            LOG.warning("Unexpected missing of sandbox_id")
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
                       flavor='m1.tiny', image='kubernetes/pause',
                       nics='auto'):
        # FIXME(hongbin): We elevate to admin privilege because the default
        # policy in nova disallows non-admin users to create instance in
        # specified host. This is not ideal because all nova instances will
        # be created at service admin tenant now, which breaks the
        # multi-tenancy model. We need to fix it.
        elevated = context.elevated()
        novaclient = nova.NovaClient(elevated)
        name = self.get_sandbox_name(container)
        if container.host != CONF.host:
            raise exception.ZunException(_(
                "Host mismatch: container should be created at host '%s'.") %
                container.host)
        # NOTE(hongbin): The format of availability zone is ZONE:HOST:NODE
        # However, we just want to specify host, so it is ':HOST:'
        az = ':%s:' % container.host
        sandbox = novaclient.create_server(name=name, image=image,
                                           flavor=flavor, key_name=key_name,
                                           nics=nics, availability_zone=az)
        self._ensure_active(novaclient, sandbox)
        sandbox_id = self._find_container_by_server_name(name)
        return sandbox_id

    def _ensure_active(self, novaclient, server, timeout=300):
        '''Wait until the Nova instance to become active.'''
        def _check_active():
            return novaclient.check_active(server)

        success_msg = "Created server %s successfully." % server.id
        timeout_msg = ("Failed to create server %s. Timeout waiting for "
                       "server to become active.") % server.id
        utils.poll_until(_check_active,
                         sleep_time=CONF.default_sleep_time,
                         time_out=timeout or CONF.default_timeout,
                         success_msg=success_msg, timeout_msg=timeout_msg)

    def delete_sandbox(self, context, sandbox_id):
        elevated = context.elevated()
        novaclient = nova.NovaClient(elevated)
        server_name = self._find_server_by_container_id(sandbox_id)
        if not server_name:
            LOG.warning("Cannot find server name for sandbox %s" %
                        sandbox_id)
            return

        server_id = novaclient.delete_server(server_name)
        self._ensure_deleted(novaclient, server_id)

    def stop_sandbox(self, context, sandbox_id):
        elevated = context.elevated()
        novaclient = nova.NovaClient(elevated)
        server_name = self._find_server_by_container_id(sandbox_id)
        if not server_name:
            LOG.warning("Cannot find server name for sandbox %s" %
                        sandbox_id)
            return
        novaclient.stop_server(server_name)

    def _ensure_deleted(self, novaclient, server_id, timeout=300):
        '''Wait until the Nova instance to be deleted.'''
        def _check_delete_complete():
            return novaclient.check_delete_server_complete(server_id)

        success_msg = "Delete server %s successfully." % server_id
        timeout_msg = ("Failed to create server %s. Timeout waiting for "
                       "server to be deleted.") % server_id
        utils.poll_until(_check_delete_complete,
                         sleep_time=CONF.default_sleep_time,
                         time_out=timeout or CONF.default_timeout,
                         success_msg=success_msg, timeout_msg=timeout_msg)

    def get_addresses(self, context, container):
        elevated = context.elevated()
        novaclient = nova.NovaClient(elevated)
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
