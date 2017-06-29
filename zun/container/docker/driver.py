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
import eventlet
import functools
import six

from docker import errors
from oslo_log import log as logging
from oslo_utils import timeutils

from zun.common import clients
from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import nova
from zun.common import utils
from zun.common.utils import check_container_id
import zun.conf
from zun.container.docker import host
from zun.container.docker import utils as docker_utils
from zun.container import driver
from zun.network import network as zun_network
from zun import objects


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
ATTACH_FLAG = "/attach/ws?logs=0&stream=1&stdin=1&stdout=1&stderr=1"


def is_not_found(e):
    return '404' in str(e)


def handle_not_found(e, context, container, do_not_raise=False):
    container.status = consts.ERROR
    container.status_reason = six.text_type(e)
    container.save(context)
    if do_not_raise:
        return

    raise exception.Conflict(message=_('the container is in Error state'))


def wrap_docker_error(function):

    @functools.wraps(function)
    def decorated_function(*args, **kwargs):
        context = args[1]
        container = args[2]
        try:
            return function(*args, **kwargs)
        except exception.DockerError as e:
            if is_not_found(e):
                handle_not_found(e, context, container)
            raise

    return decorated_function


class DockerDriver(driver.ContainerDriver):
    """Implementation of container drivers for Docker."""

    def __init__(self):
        super(DockerDriver, self).__init__()
        self._host = host.Host()

    def load_image(self, image_path=None):
        with docker_utils.docker_client() as docker:
            if image_path:
                with open(image_path, 'rb') as fd:
                    LOG.debug('Loading local image %s into docker', image_path)
                    docker.load_image(fd)

    def inspect_image(self, image):
        with docker_utils.docker_client() as docker:
            LOG.debug('Inspecting image %s', image)
            return docker.inspect_image(image)

    def get_image(self, name):
        LOG.debug('Obtaining image %s', name)
        with docker_utils.docker_client() as docker:
            return docker.get_image(name)

    def images(self, repo, quiet=False):
        with docker_utils.docker_client() as docker:
            return docker.images(repo, quiet)

    def create(self, context, container, sandbox_id, image):
        with docker_utils.docker_client() as docker:
            name = container.name
            image = container.image
            LOG.debug('Creating container with image %(image)s name %(name)s',
                      {'image': image, 'name': name})

            kwargs = {
                'name': self.get_container_name(container),
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
                'labels': container.labels,
                'tty': container.interactive,
                'stdin_open': container.interactive,
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
            container.status = consts.CREATED
            container.status_reason = None
            container.save(context)
            return container

    def _provision_network(self, context, container, network_api):
        LOG.debug('Creating networks for container with image %(image)s '
                  'name %(name)s',
                  {'image': container.image, 'name': container.name})
        # Find an available neutron net and create docker network by
        # wrapping the neutron net.
        neutron_net = self._get_available_network(context)
        network = self._get_or_create_docker_network(
            context, network_api, neutron_net['id'])
        return network

    def _setup_network_for_container(self, context, container,
                                     requested_networks, network_api):
        sandbox_id = self.get_sandbox_id(container)
        security_group_ids = self._get_security_group_ids(
            context, container.security_groups)
        # Container connects to the bridge network by default so disconnect
        # the container from it before connecting it to neutron network.
        # This avoids potential conflict between these two networks.
        network_api.disconnect_container_from_network(container, 'bridge',
                                                      sandbox_id)
        addresses = {}
        for network in requested_networks:
            network_name = network['network']
            addrs = network_api.connect_container_to_network(
                container, network_name, sandbox_id=sandbox_id,
                security_groups=security_group_ids)
            addresses[network_name] = addrs

        return addresses

    def delete(self, container, force):
        with docker_utils.docker_client() as docker:
            if container.container_id:
                try:
                    docker.remove_container(container.container_id,
                                            force=force)
                except errors.APIError as api_error:
                    if is_not_found(api_error):
                        return
                    raise

    def _cleanup_network_for_container(self, container, network_api,
                                       sandbox_id):
        for name in container.addresses:
            network_api.disconnect_container_from_network(container, name,
                                                          sandbox_id)

    def list(self, context):
        id_to_container_map = {}
        with docker_utils.docker_client() as docker:
            id_to_container_map = {c['Id']: c
                                   for c in docker.list_containers()}

        db_containers = objects.Container.list_by_host(context, CONF.host)
        for db_container in db_containers:
            container_id = db_container.container_id
            docker_container = id_to_container_map.get(container_id)
            if docker_container:
                self._populate_container(db_container, docker_container)
            else:
                if db_container.status != consts.CREATING:
                    # Print a warning message if the container was recorded in
                    # DB but missing in docker.
                    LOG.warning("Container was recorded in DB but missing in "
                                "docker")

        return db_containers

    def update_containers_states(self, context, containers):
        db_containers = self.list(context)
        if not db_containers:
            return

        id_to_db_container_map = {container.container_id: container
                                  for container in db_containers}
        id_to_container_map = {container.container_id: container
                               for container in containers}

        for cid in (six.viewkeys(id_to_container_map) &
                    six.viewkeys(id_to_db_container_map)):
            container = id_to_container_map[cid]
            # sync status
            db_container = id_to_db_container_map[cid]
            if container.status != db_container.status:
                old_status = container.status
                container.status = db_container.status
                container.save(context)
                LOG.info('Status of container %s changed from %s to %s',
                         container.uuid, old_status, container.status)
            # sync host
            # Note(kiennt): Current host.
            cur_host = CONF.host
            if container.host != cur_host:
                old_host = container.host
                container.host = cur_host
                container.save(context)
                LOG.info('Host of container %s changed from %s to %s',
                         container.uuid, old_host, container.host)

    def show(self, context, container):
        with docker_utils.docker_client() as docker:
            if container.container_id is None:
                return container

            response = None
            try:
                response = docker.inspect_container(container.container_id)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    handle_not_found(api_error, context, container,
                                     do_not_raise=True)
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
        state = response.get('State')
        if type(state) is dict:
            status_detail = ''
            if state.get('Error'):
                container.status = consts.ERROR
                status_detail = self.format_status_detail(
                    state.get('FinishedAt'))
                container.status_detail = "Exited({}) {} ago " \
                    "(error)".format(state.get('ExitCode'), status_detail)
            elif state.get('Paused'):
                container.status = consts.PAUSED
                status_detail = self.format_status_detail(
                    state.get('StartedAt'))
                container.status_detail = "Up {} (paused)".format(
                    status_detail)
            elif state.get('Running'):
                container.status = consts.RUNNING
                status_detail = self.format_status_detail(
                    state.get('StartedAt'))
                container.status_detail = "Up {}".format(
                    status_detail)
            else:
                started_at = self.format_status_detail(state.get('StartedAt'))
                finished_at = self.format_status_detail(
                    state.get('FinishedAt'))
                if started_at == "":
                    container.status = consts.CREATED
                    container.status_detail = "Created"
                elif finished_at == "":
                    container.status = consts.UNKNOWN
                    container.status_detail = ""
                else:
                    container.status = consts.STOPPED
                    container.status_detail = "Exited({}) {} ago ".format(
                        state.get('ExitCode'), finished_at)
            if status_detail is None:
                container.status_detail = None
        else:
            if state.lower() == 'created':
                container.status = consts.CREATED
            elif state.lower() == 'paused':
                container.status = consts.PAUSED
            elif state.lower() == 'running':
                container.status = consts.RUNNING
            elif state.lower() == 'dead':
                container.status = consts.ERROR
            elif state.lower() in ('restarting', 'exited', 'removing'):
                container.status = consts.STOPPED
            else:
                container.status = consts.UNKNOWN
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
    @wrap_docker_error
    def reboot(self, context, container, timeout):
        with docker_utils.docker_client() as docker:
            if timeout:
                docker.restart(container.container_id,
                               timeout=int(timeout))
            else:
                docker.restart(container.container_id)
            container.status = consts.RUNNING
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def stop(self, context, container, timeout):
        with docker_utils.docker_client() as docker:
            if timeout:
                docker.stop(container.container_id,
                            timeout=int(timeout))
            else:
                docker.stop(container.container_id)
            container.status = consts.STOPPED
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def start(self, context, container):
        with docker_utils.docker_client() as docker:
            docker.start(container.container_id)
            container.status = consts.RUNNING
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def pause(self, context, container):
        with docker_utils.docker_client() as docker:
            docker.pause(container.container_id)
            container.status = consts.PAUSED
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def unpause(self, context, container):
        with docker_utils.docker_client() as docker:
            docker.unpause(container.container_id)
            container.status = consts.RUNNING
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def show_logs(self, context, container, stdout=True, stderr=True,
                  timestamps=False, tail='all', since=None):
        with docker_utils.docker_client() as docker:
            try:
                tail = int(tail)
            except ValueError:
                tail = 'all'

            if since is None or since == 'None':
                return docker.logs(container.container_id, stdout, stderr,
                                   False, timestamps, tail, None)
            else:
                try:
                    since = int(since)
                except ValueError:
                    try:
                        since = datetime.datetime.strptime(
                            since, '%Y-%m-%d %H:%M:%S,%f')
                    except Exception:
                        raise
                return docker.logs(container.container_id, stdout, stderr,
                                   False, timestamps, tail, since)

    @check_container_id
    @wrap_docker_error
    def execute_create(self, context, container, command, interactive=False):
        stdin = True if interactive else False
        tty = True if interactive else False
        with docker_utils.docker_client() as docker:
            create_res = docker.exec_create(
                container.container_id, command, stdin=stdin, tty=tty)
            exec_id = create_res['Id']
            return exec_id

    def execute_run(self, exec_id, command):
        with docker_utils.docker_client() as docker:
            try:
                with eventlet.Timeout(CONF.docker.execute_timeout):
                    output = docker.exec_start(exec_id, False, False, False)
            except eventlet.Timeout:
                raise exception.Conflict(_(
                    "Timeout on executing command: %s") % command)
            inspect_res = docker.exec_inspect(exec_id)
            return {"output": output, "exit_code": inspect_res['ExitCode']}

    def execute_resize(self, exec_id, height, width):
        height = int(height)
        width = int(width)
        with docker_utils.docker_client() as docker:
            try:
                docker.exec_resize(exec_id, height=height, width=width)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    raise exception.Invalid(_(
                        "no such exec instance: %s") % str(api_error))
                raise

    @check_container_id
    @wrap_docker_error
    def kill(self, context, container, signal=None):
        with docker_utils.docker_client() as docker:
            if signal is None or signal == 'None':
                docker.kill(container.container_id)
            else:
                docker.kill(container.container_id, signal)
            return container

    @check_container_id
    @wrap_docker_error
    def update(self, context, container):
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
            return docker.update_container(container.container_id, **args)

    @check_container_id
    def get_websocket_url(self, context, container):
        version = CONF.docker.docker_remote_api_version
        remote_api_host = CONF.docker.docker_remote_api_host
        remote_api_port = CONF.docker.docker_remote_api_port
        url = "ws://" + remote_api_host + ":" + remote_api_port + \
              "/v" + version + "/containers/" + container.container_id \
              + ATTACH_FLAG
        return url

    @check_container_id
    @wrap_docker_error
    def resize(self, context, container, height, width):
        with docker_utils.docker_client() as docker:
            height = int(height)
            width = int(width)
            docker.resize(container.container_id, height, width)
            return container

    @check_container_id
    @wrap_docker_error
    def top(self, context, container, ps_args=None):
        with docker_utils.docker_client() as docker:
            if ps_args is None or ps_args == 'None':
                return docker.top(container.container_id)
            else:
                return docker.top(container.container_id, ps_args)

    @check_container_id
    @wrap_docker_error
    def get_archive(self, context, container, path):
        with docker_utils.docker_client() as docker:
            stream, stat = docker.get_archive(container.container_id, path)
            filedata = stream.read()
            return filedata, stat

    @check_container_id
    @wrap_docker_error
    def put_archive(self, context, container, path, data):
        with docker_utils.docker_client() as docker:
            docker.put_archive(container.container_id, path, data)

    @check_container_id
    @wrap_docker_error
    def stats(self, context, container):
        with docker_utils.docker_client() as docker:
            res = docker.stats(container.container_id, decode=False,
                               stream=False)

            cpu_usage = res['cpu_stats']['cpu_usage']['total_usage']
            system_cpu_usage = res['cpu_stats']['system_cpu_usage']
            cpu_percent = float(cpu_usage) / float(system_cpu_usage) * 100
            mem_usage = res['memory_stats']['usage'] / 1024 / 1024
            mem_limit = res['memory_stats']['limit'] / 1024 / 1024
            mem_percent = float(mem_usage) / float(mem_limit) * 100

            blk_stats = res['blkio_stats']['io_service_bytes_recursive']
            io_read = 0
            io_write = 0
            for item in blk_stats:
                if 'Read' == item['op']:
                    io_read = io_read + item['value']
                if 'Write' == item['op']:
                    io_write = io_write + item['value']

            net_stats = res['networks']
            net_rxb = 0
            net_txb = 0
            for k, v in net_stats.items():
                net_rxb = net_rxb + v['rx_bytes']
                net_txb = net_txb + v['tx_bytes']

            stats = {"CONTAINER": container.name,
                     "CPU %": cpu_percent,
                     "MEM USAGE(MiB)": mem_usage,
                     "MEM LIMIT(MiB)": mem_limit,
                     "MEM %": mem_percent,
                     "BLOCK I/O(B)": str(io_read) + "/" + str(io_write),
                     "NET I/O(B)": str(net_rxb) + "/" + str(net_txb)}
            return stats

    @check_container_id
    @wrap_docker_error
    def commit(self, context, container, repository=None, tag=None):
        with docker_utils.docker_client() as docker:
            repository = str(repository)
            if tag is None or tag == "None":
                return docker.commit(container.container_id, repository)
            else:
                tag = str(tag)
                return docker.commit(container.container_id, repository, tag)

    def _encode_utf8(self, value):
        if six.PY2 and not isinstance(value, six.text_type):
            value = six.text_type(value)
        return value.encode('utf-8')

    def create_sandbox(self, context, container, image='kubernetes/pause',
                       requested_networks=None):
        with docker_utils.docker_client() as docker:
            network_api = zun_network.api(context=context, docker_api=docker)
            if not requested_networks:
                network = self._provision_network(context, container,
                                                  network_api)
                requested_networks = [{'network': network['Name'],
                                       'port': '',
                                       'v4-fixed-ip': '',
                                       'v6-fixed-ip': ''}]
            name = self.get_sandbox_name(container)
            sandbox = docker.create_container(image, name=name,
                                              hostname=name[:63])
            self.set_sandbox_id(container, sandbox['Id'])
            addresses = self._setup_network_for_container(
                context, container, requested_networks, network_api)
            container.addresses = addresses
            container.save(context)

            docker.start(sandbox['Id'])
            return sandbox['Id']

    def _get_security_group_ids(self, context, security_groups):
        if security_groups is None:
            return None
        else:
            neutron = clients.OpenStackClients(context).neutron()
            search_opts = {'tenant_id': context.project_id}
            security_groups_list = neutron.list_security_groups(
                **search_opts).get('security_groups', [])
            security_group_ids = [item['id'] for item in security_groups_list
                                  if item['name'] in security_groups]
            if len(security_group_ids) == len(security_groups):
                return security_group_ids
            else:
                raise exception.ZunException(_(
                    "Any of the security group in %s is not found ") %
                    security_groups)

    def _get_available_network(self, context):
        neutron = clients.OpenStackClients(context).neutron()
        search_opts = {'tenant_id': context.project_id, 'shared': False}
        nets = neutron.list_networks(**search_opts).get('networks', [])
        if not nets:
            raise exception.ZunException(_(
                "There is no neutron network available"))
        nets.sort(key=lambda x: x['created_at'])
        return nets[0]

    def _get_or_create_docker_network(self, context, network_api,
                                      neutron_net_id):
        # Append project_id to the network name to avoid name collision
        # across projects.
        docker_net_name = neutron_net_id + '-' + context.project_id
        docker_networks = network_api.list_networks(names=[docker_net_name])
        if not docker_networks:
            network_api.create_network(neutron_net_id=neutron_net_id,
                                       name=docker_net_name)
            docker_networks = network_api.list_networks(
                names=[docker_net_name])

        return docker_networks[0]

    def delete_sandbox(self, context, container, sandbox_id):
        with docker_utils.docker_client() as docker:
            network_api = zun_network.api(context=context, docker_api=docker)
            self._cleanup_network_for_container(container, network_api,
                                                sandbox_id)
            try:
                docker.remove_container(sandbox_id, force=True)
            except errors.APIError as api_error:
                if is_not_found(api_error):
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

    def get_host_info(self):
        with docker_utils.docker_client() as docker:
            info = docker.info()
            total = info['Containers']
            paused = info['ContainersPaused']
            running = info['ContainersRunning']
            stopped = info['ContainersStopped']
            cpus = info['NCPU']
            architecture = info['Architecture']
            os_type = info['OSType']
            os = info['OperatingSystem']
            kernel_version = info['KernelVersion']
            labels = {}
            slabels = info['Labels']
            if slabels:
                for l in slabels:
                    kv = l.split("=")
                    label = {kv[0]: kv[1]}
                    labels.update(label)
            return (total, running, paused, stopped, cpus,
                    architecture, os_type, os, kernel_version, labels)

    def get_cpu_used(self):
        cpu_used = 0
        with docker_utils.docker_client() as docker:
            containers = docker.containers()
            for container in containers:
                cnt_id = container['Id']
                # Fixme: if there is a way to get all container inspect info
                # for one call only?
                inspect = docker.inspect_container(cnt_id)
                cpu_period = inspect['HostConfig']['CpuPeriod']
                cpu_quota = inspect['HostConfig']['CpuQuota']
                if cpu_period and cpu_quota:
                    cpu_used += float(cpu_quota) / cpu_period
                else:
                    if 'NanoCpus' in inspect['HostConfig']:
                        nanocpus = inspect['HostConfig']['NanoCpus']
                        cpu_used += float(nanocpus) / 1e9
            return cpu_used

    def add_security_group(self, context, container, security_group,
                           sandbox_id=None):
        security_group_ids = self._get_security_group_ids(
            context, [security_group])
        with docker_utils.docker_client() as docker:
            network_api = zun_network.api(context=context, docker_api=docker)
            sandbox = docker.inspect_container(sandbox_id)
            for network in sandbox["NetworkSettings"]["Networks"]:
                network_api.add_security_groups_to_ports(
                    container, security_group_ids, sandbox_id)

    def get_available_nodes(self):
        return [self._host.get_hostname()]


class NovaDockerDriver(DockerDriver):
    def add_security_group(self, context, container, security_group, **kwargs):
        msg = "NovaDockerDriver does not support security_groups"
        raise exception.ZunException(msg)

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
        """Wait until the Nova instance to become active."""
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
            LOG.warning("Cannot find server name for sandbox %s", sandbox_id)
            return

        server_id = novaclient.delete_server(server_name)
        self._ensure_deleted(novaclient, server_id)

    def stop_sandbox(self, context, sandbox_id):
        elevated = context.elevated()
        novaclient = nova.NovaClient(elevated)
        server_name = self._find_server_by_container_id(sandbox_id)
        if not server_name:
            LOG.warning("Cannot find server name for sandbox %s", sandbox_id)
            return
        novaclient.stop_server(server_name)

    def _ensure_deleted(self, novaclient, server_id, timeout=300):
        """Wait until the Nova instance to be deleted."""
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
