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
import errno
import eventlet
import functools
import types

from docker import errors
from neutronclient.common import exceptions as n_exc
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
import psutil
import tenacity

from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
from zun.common.utils import check_container_id
from zun.compute import container_actions
import zun.conf
from zun.container.docker import host
from zun.container.docker import utils as docker_utils
from zun.container import driver
from zun.image import driver as img_driver
from zun.network import network as zun_network
from zun import objects

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
ATTACH_FLAG = "/attach/ws?logs=0&stream=1&stdin=1&stdout=1&stderr=1"


def is_not_found(e):
    return '404' in str(e)


def is_not_connected(e):
    # Test the following exception:
    #
    #   500 Server Error: Internal Server Error ("container XXX is not
    #   connected to the network XXX")
    #
    # Note(hongbin): Docker should response a 4xx instead of 500. This looks
    # like a bug from docker side: https://github.com/moby/moby/issues/35888
    return ' is not connected to the network ' in str(e)


def is_conflict(e):
    conflict_infos = ['not running', 'not paused', 'paused']
    for info in conflict_infos:
        if info in str(e):
            return True
    return False


def handle_not_found(e, context, container, do_not_raise=False):
    if container.status == consts.DELETING:
        return

    if container.auto_remove:
        container.status = consts.DELETED
    else:
        container.status = consts.ERROR
        container.status_reason = str(e)
    container.save(context)
    if do_not_raise:
        return

    raise exception.Conflict(message=_(
        "Cannot act on container in '%s' state") % container.status)


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
            if is_conflict(e):
                raise exception.Conflict(_("%s") % str(e))
            raise

    return decorated_function


class DockerDriver(driver.BaseDriver, driver.ContainerDriver,
                   driver.CapsuleDriver):
    """Implementation of container drivers for Docker."""

    # TODO(hongbin): define a list of capabilities of this driver.
    capabilities = {}

    def __init__(self):
        super(DockerDriver, self).__init__()
        self._host = host.Host()
        self._get_host_storage_info()
        self.image_drivers = {}
        for driver_name in CONF.image_driver_list:
            driver = img_driver.load_image_driver(driver_name)
            self.image_drivers[driver_name] = driver

    def _get_host_storage_info(self):
        host_info = self.get_host_info()
        self.docker_root_dir = host_info['docker_root_dir']
        storage_info = self._host.get_storage_info()
        self.base_device_size = storage_info['default_base_size']
        self.support_disk_quota = self._host.check_supported_disk_quota(
            host_info)

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

    def delete_image(self, context, img_id, image_driver=None):
        image = self.inspect_image(img_id)['RepoTags'][0]
        if image_driver:
            image_driver_list = [image_driver.lower()]
        else:
            image_driver_list = CONF.image_driver_list
        for driver_name in image_driver_list:
            try:
                image_driver = img_driver.load_image_driver(driver_name)
                if driver_name == 'glance':
                    image_driver.delete_image_tar(context, image)
                elif driver_name == 'docker':
                    image_driver.delete_image(context, img_id)
            except exception.ZunException:
                LOG.exception('Unknown exception occurred while deleting '
                              'image %s', img_id)

    def delete_committed_image(self, context, img_id, image_driver):
        try:
            image_driver.delete_committed_image(context, img_id)
        except Exception as e:
            LOG.exception('Unknown exception occurred while '
                          'deleting image %s: %s',
                          img_id,
                          str(e))
            raise exception.ZunException(str(e))

    def images(self, repo, quiet=False):
        with docker_utils.docker_client() as docker:
            return docker.images(repo, quiet)

    def pull_image(self, context, repo, tag, image_pull_policy='always',
                   driver_name=None, registry=None):
        if driver_name is None:
            driver_name = CONF.default_image_driver

        try:
            image_driver = self.image_drivers[driver_name]
            image, image_loaded = image_driver.pull_image(
                context, repo, tag, image_pull_policy, registry)
            if image:
                image['driver'] = driver_name.split('.')[0]
        except exception.ZunException:
            raise
        except Exception as e:
            LOG.exception('Unknown exception occurred while loading '
                          'image: %s', str(e))
            raise exception.ZunException(str(e))

        return image, image_loaded

    def search_image(self, context, repo, tag, driver_name, exact_match):
        if driver_name is None:
            driver_name = CONF.default_image_driver

        try:
            image_driver = self.image_drivers[driver_name]
            return image_driver.search_image(context, repo, tag,
                                             exact_match)
        except exception.ZunException:
            raise
        except Exception as e:
            LOG.exception('Unknown exception occurred while searching '
                          'for image: %s', str(e))
            raise exception.ZunException(str(e))

    def create_image(self, context, image_name, image_driver):
        try:
            img = image_driver.create_image(context, image_name)
        except Exception as e:
            LOG.exception('Unknown exception occurred while creating '
                          'image: %s', str(e))
            raise exception.ZunException(str(e))
        return img

    def upload_image_data(self, context, image, image_tag, image_data,
                          image_driver):
        try:
            image_driver.update_image(context,
                                      image.id,
                                      tag=image_tag)
            # Image data has to match the image format.
            # contain format defaults to 'docker';
            # disk format defaults to 'qcow2'.
            img = image_driver.upload_image_data(context,
                                                 image.id,
                                                 image_data)
        except Exception as e:
            LOG.exception('Unknown exception occurred while uploading '
                          'image: %s', str(e))
            raise exception.ZunException(str(e))
        return img

    def read_tar_image(self, image):
        with docker_utils.docker_client() as docker:
            LOG.debug('Reading local tar image %s ', image['path'])
            try:
                docker.read_tar_image(image)
            except Exception:
                LOG.warning("Unable to read image data from tarfile")

    def create(self, context, container, image, requested_networks,
               requested_volumes):
        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            name = container.name
            if image['tag']:
                image_repo = image['repo'] + ":" + image['tag']
            else:
                image_repo = image['repo']
            LOG.debug('Creating container with image %(image)s name %(name)s',
                      {'image': image_repo, 'name': name})
            self._provision_network(context, network_driver,
                                    requested_networks)
            volmaps = requested_volumes.get(container.uuid, [])
            binds = self._get_binds(context, volmaps)

            entrypoint = container.entrypoint
            command = container.command
            if not entrypoint or not command:
                image_dict = docker.inspect_image(image_repo)
                container.entrypoint = entrypoint or \
                    image_dict['Config']['Entrypoint']
                container.command = command or image_dict['Config']['Cmd']
            kwargs = {
                'name': self.get_container_name(container),
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
                'labels': container.labels,
                'tty': container.tty,
                'stdin_open': container.interactive,
                'hostname': container.hostname,
                'entrypoint': container.entrypoint,
            }

            if not self._is_runtime_supported():
                if container.runtime:
                    raise exception.ZunException(_(
                        'Specifying runtime in Docker API is not supported'))
                runtime = None
            else:
                runtime = container.runtime or CONF.container_runtime

            host_config = {}
            host_config['privileged'] = container.privileged
            host_config['runtime'] = runtime
            host_config['binds'] = binds
            kwargs['volumes'] = [b['bind'] for b in binds.values()]
            self._process_exposed_ports(network_driver.neutron_api, container,
                                        kwargs)
            # Process the first requested network at create time. The rest
            # will be processed after create.
            requested_network = requested_networks.pop()
            security_group_ids = utils.get_security_group_ids(
                context, container.security_groups)
            network_driver.process_networking_config(
                container, requested_network, host_config, kwargs, docker,
                security_group_ids=security_group_ids)
            if container.auto_remove:
                host_config['auto_remove'] = container.auto_remove
            if self._should_limit_memory(container):
                host_config['mem_limit'] = str(container.memory) + 'M'
            if self._should_limit_cpu(container):
                host_config['cpu_shares'] = int(1024 * container.cpu)
            if container.restart_policy:
                count = int(container.restart_policy['MaximumRetryCount'])
                name = container.restart_policy['Name']
                host_config['restart_policy'] = {'Name': name,
                                                 'MaximumRetryCount': count}

            if container.disk:
                disk_size = str(container.disk) + 'G'
                host_config['storage_opt'] = {'size': disk_size}
            if container.cpu_policy == 'dedicated':
                host_config['cpuset_cpus'] = container.cpuset.cpuset_cpus
                host_config['cpuset_mems'] = str(container.cpuset.cpuset_mems)
            # The time unit in docker of heath checking is us, and the unit
            # of interval and timeout is seconds.
            if container.healthcheck:
                healthcheck = {}
                healthcheck['test'] = container.healthcheck.get('test', '')
                interval = container.healthcheck.get('interval', 0)
                healthcheck['interval'] = interval * 10 ** 9
                healthcheck['retries'] = int(container.healthcheck.
                                             get('retries', 0))
                timeout = container.healthcheck.get('timeout', 0)
                healthcheck['timeout'] = timeout * 10 ** 9
                kwargs['healthcheck'] = healthcheck

            kwargs['host_config'] = docker.create_host_config(**host_config)
            response = docker.create_container(image_repo, **kwargs)
            container.container_id = response['Id']

            addresses = self._setup_network_for_container(
                context, container, requested_networks, network_driver)
            container.addresses = addresses

            response = docker.inspect_container(container.container_id)
            self._populate_container(container, response, force=True)
            container.save(context)
            return container

    def _should_limit_memory(self, container):
        return (container.memory is not None and
                not isinstance(container, objects.Capsule))

    def _should_limit_cpu(self, container):
        return (container.cpu is not None and
                not isinstance(container, objects.Capsule))

    def _is_runtime_supported(self):
        return float(CONF.docker.docker_remote_api_version) >= 1.26

    def node_support_disk_quota(self):
        return self.support_disk_quota

    def get_host_default_base_size(self):
        return self.base_device_size

    def _process_exposed_ports(self, neutron_api, container, kwargs):
        exposed_ports = {}
        if isinstance(container, objects.Container):
            exposed_ports.update(container.exposed_ports or {})
        if isinstance(container, objects.Capsule):
            for container in (container.init_containers +
                              container.containers):
                exposed_ports.update(container.exposed_ports or {})

        if not exposed_ports:
            return

        # process security group
        secgroup_name = self._get_secgorup_name(container.uuid)
        secgroup_id = neutron_api.create_security_group({'security_group': {
            "name": secgroup_name}})['security_group']['id']
        neutron_api.expose_ports(secgroup_id, exposed_ports)
        if container.security_groups:
            container.security_groups.append(secgroup_id)
        else:
            container.security_groups = [secgroup_id]
        # process kwargs on creating the docker container
        ports = []
        for port in exposed_ports:
            port, proto = port.split('/')
            ports.append((port, proto))
        kwargs['ports'] = ports

    def _provision_network(self, context, network_driver, requested_networks):
        for rq_network in requested_networks:
            network_driver.get_or_create_network(context,
                                                 rq_network['network'])

    def _get_secgorup_name(self, container_uuid):
        return consts.NAME_PREFIX + container_uuid

    def _get_binds(self, context, requested_volumes):
        binds = {}
        for volume in requested_volumes:
            volume_driver = self._get_volume_driver(volume)
            source, destination = volume_driver.bind_mount(context, volume)
            binds[source] = {'bind': destination}
        return binds

    def _setup_network_for_container(self, context, container,
                                     requested_networks, network_driver):
        security_group_ids = utils.get_security_group_ids(
            context, container.security_groups)
        addresses = {}
        if container.addresses:
            addresses = container.addresses
        for network in requested_networks:
            if network['network'] in addresses:
                # This network is already setup so skip it
                continue

            addrs = network_driver.connect_container_to_network(
                container, network, security_groups=security_group_ids)
            addresses[network['network']] = addrs

        return addresses

    def delete(self, context, container, force):
        with docker_utils.docker_client() as docker:
            try:
                network_driver = zun_network.driver(context=context,
                                                    docker_api=docker)
                self._cleanup_network_for_container(container, network_driver)
                self._cleanup_exposed_ports(network_driver.neutron_api,
                                            container)
                if container.container_id:
                    docker.remove_container(container.container_id,
                                            force=force)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    return
                if is_not_connected(api_error):
                    return
                raise

    @wrap_docker_error
    def _cleanup_network_for_container(self, container, network_driver):
        if not container.addresses:
            return
        for neutron_net in container.addresses:
            network_driver.disconnect_container_from_network(
                container, neutron_net)

    def _cleanup_exposed_ports(self, neutron_api, container):
        exposed_ports = {}
        if isinstance(container, objects.Container):
            exposed_ports.update(container.exposed_ports or {})
        if isinstance(container, objects.Capsule):
            for container in (container.init_containers +
                              container.containers):
                exposed_ports.update(container.exposed_ports or {})
        if not exposed_ports:
            return

        try:
            neutron_api.delete_security_group(container.security_groups[0])
        except n_exc.NeutronClientException:
            LOG.exception("Failed to delete security group")

    def check_container_exist(self, container):
        with docker_utils.docker_client() as docker:
            docker_containers = [c['Id']
                                 for c in docker.list_containers()]
            if container.container_id not in docker_containers:
                return False
        return True

    def list(self, context):
        non_existent_containers = []
        with docker_utils.docker_client() as docker:
            docker_containers = docker.list_containers()
            id_to_container_map = {c['Id']: c
                                   for c in docker_containers}
            uuids = self._get_container_uuids(docker_containers)

        local_containers = self._get_local_containers(context, uuids)
        for container in local_containers:
            if container.status in (consts.CREATING, consts.DELETING,
                                    consts.DELETED):
                # Skip populating db record since the container is in a
                # unstable state.
                continue

            container_id = container.container_id
            docker_container = id_to_container_map.get(container_id)
            if not container_id or not docker_container:
                non_existent_containers.append(container)
                continue

            self._populate_container(container, docker_container)

        return local_containers, non_existent_containers

    def heal_with_rebuilding_container(self, context, container, manager):
        if not container.container_id:
            return

        rebuild_status = utils.VALID_STATES['rebuild']
        try:
            if (container.auto_heal and
                    container.status in rebuild_status):
                context.project_id = container.project_id
                objects.ContainerAction.action_start(
                    context, container.uuid, container_actions.REBUILD,
                    want_result=False)
                manager.container_rebuild(context, container)
            else:
                LOG.warning("Container %s was recorded in DB but "
                            "missing in docker", container.uuid)
                container.status = consts.ERROR
                msg = "No such container: %s in docker" % \
                      (container.container_id)
                container.status_reason = str(msg)
                container.save(context)
        except Exception as e:
            LOG.warning("heal container with rebuilding failed, "
                        "err code: %s", e)

    def _get_container_uuids(self, containers):
        # The name of Docker container is of the form '/zun-<uuid>'
        name_prefix = '/' + consts.NAME_PREFIX
        uuids = [c['Names'][0].replace(name_prefix, '', 1)
                 for c in containers]
        return [u for u in uuids if uuidutils.is_uuid_like(u)]

    def _get_local_containers(self, context, uuids):
        host_containers = objects.Container.list_by_host(context, CONF.host)
        uuids = list(set(uuids) | set([c.uuid for c in host_containers]))
        containers = objects.Container.list(context,
                                            filters={'uuid': uuids})
        return containers

    def update_containers_states(self, context, containers, manager):
        local_containers, non_existent_containers = self.list(context)
        if not local_containers:
            return

        id_to_local_container_map = {container.container_id: container
                                     for container in local_containers
                                     if container.container_id}
        id_to_container_map = {container.container_id: container
                               for container in containers
                               if container.container_id}

        for cid in (id_to_container_map.keys() &
                    id_to_local_container_map.keys()):
            container = id_to_container_map[cid]
            # sync status
            local_container = id_to_local_container_map[cid]
            if container.status != local_container.status:
                old_status = container.status
                container.status = local_container.status
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
        for container in non_existent_containers:
            if container.host == CONF.host:
                if container.auto_remove:
                    container.status = consts.DELETED
                    container.save(context)
                else:
                    self.heal_with_rebuilding_container(context, container,
                                                        manager)

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
        time_dict['hours'] = delta.seconds // 3600
        time_dict['minutes'] = (delta.seconds % 3600) // 60
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

    def _populate_container(self, container, response, force=False):
        state = response.get('State')
        self._populate_container_state(container, state, force)

        config = response.get('Config')
        if config:
            self._populate_hostname_and_ports(container, config)

        hostconfig = response.get('HostConfig')
        if hostconfig:
            container.runtime = hostconfig.get('Runtime')

    def _populate_container_state(self, container, state, force):
        if container.task_state and not force:
            # NOTE(hongbin): we don't want to populate container state
            # if another thread is performing task on this container.
            # In this case, task_state will be assigned (which means there is a
            # task performing on this container) and 'force' will be set to
            # False. For example, if this method is called by create,
            # 'force' will be set to True to force refreshing the state.
            # If this method is called by list or show,
            # 'force' will be set to False, in which case we skip
            # refreshing the state if there is a task on this container.
            return

        if not state:
            LOG.warning('Receive unexpected state from docker: %s', state)
            container.status = consts.UNKNOWN
            container.status_reason = _("container state is missing")
            container.status_detail = None
        elif type(state) is dict:
            status_detail = ''
            if state.get('Error'):
                if state.get('Status') in ('exited', 'removing'):
                    container.status = consts.STOPPED
                else:
                    status = state.get('Status').capitalize()
                    if status in consts.CONTAINER_STATUSES:
                        container.status = status
                status_detail = self.format_status_detail(
                    state.get('FinishedAt'))
                container.status_detail = "Exited({}) {} ago (error)".format(
                    state.get('ExitCode'), status_detail)
            elif state.get('Paused'):
                container.status = consts.PAUSED
                status_detail = self.format_status_detail(
                    state.get('StartedAt'))
                container.status_detail = "Up {} (paused)".format(
                    status_detail)
            elif state.get('Restarting'):
                container.status = consts.RESTARTING
                container.status_detail = "Restarting"
            elif state.get('Running'):
                container.status = consts.RUNNING
                status_detail = self.format_status_detail(
                    state.get('StartedAt'))
                container.status_detail = "Up {}".format(
                    status_detail)
            elif state.get('Dead'):
                container.status = consts.DEAD
                container.status_detail = "Dead"
            else:
                started_at = self.format_status_detail(state.get('StartedAt'))
                finished_at = self.format_status_detail(
                    state.get('FinishedAt'))
                if started_at == "" and container.status == consts.CREATING:
                    container.status = consts.CREATED
                    container.status_detail = "Created"
                elif (started_at == "" and
                      container.status in (consts.CREATED, consts.RESTARTING,
                                           consts.ERROR, consts.REBUILDING)):
                    pass
                elif started_at != "" and finished_at == "":
                    LOG.warning('Receive unexpected state from docker: %s',
                                state)
                    container.status = consts.UNKNOWN
                    container.status_reason = _("unexpected container state")
                    container.status_detail = ""
                elif started_at != "" and finished_at != "":
                    container.status = consts.STOPPED
                    container.status_detail = "Exited({}) {} ago ".format(
                        state.get('ExitCode'), finished_at)
            if status_detail is None:
                container.status_detail = None
        else:
            state = state.lower()
            if state == 'created' and container.status == consts.CREATING:
                container.status = consts.CREATED
            elif (state == 'created' and
                  container.status in (consts.CREATED, consts.RESTARTING,
                                       consts.ERROR, consts.REBUILDING)):
                pass
            elif state == 'paused':
                container.status = consts.PAUSED
            elif state == 'running':
                container.status = consts.RUNNING
            elif state == 'dead':
                container.status = consts.DEAD
            elif state == 'restarting':
                container.status = consts.RESTARTING
            elif state in ('exited', 'removing'):
                container.status = consts.STOPPED
            else:
                LOG.warning('Receive unexpected state from docker: %s', state)
                container.status = consts.UNKNOWN
                container.status_reason = _("unexpected container state")
            container.status_detail = None

    def _populate_hostname_and_ports(self, container, config):
        # populate hostname only when container.hostname wasn't set
        if container.hostname is None:
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
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            network_driver.on_container_started(container)
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
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            try:
                network_driver.on_container_stopped(container)
            except Exception as e:
                LOG.error('network driver failed on stopping container: %s',
                          str(e))
            return container

    @check_container_id
    @wrap_docker_error
    def start(self, context, container):
        with docker_utils.docker_client() as docker:
            docker.start(container.container_id)
            container.status = consts.RUNNING
            container.status_reason = None
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            try:
                network_driver.on_container_started(container)
            except Exception as e:
                LOG.error('network driver failed on starting container: %s',
                          str(e))
                try:
                    docker.stop(container.container_id, timeout=5)
                    LOG.debug('Stop container successfully')
                    network_driver.on_container_stopped(container)
                    LOG.debug('Network driver clean up successfully')
                except Exception:
                    pass
                container.status = consts.STOPPED
                container.status_reason = _("failed to configure network")
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
            return output, inspect_res['ExitCode']

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
            container.status = consts.STOPPED
            container.status_reason = None
            return container

    @check_container_id
    @wrap_docker_error
    def update(self, context, container):
        patch = container.obj_get_changes()

        args = {}
        memory = patch.get('memory')
        if memory is not None:
            args['mem_limit'] = str(memory) + 'M'
            args['memswap_limit'] = CONF.default_memory_swap
        cpu = patch.get('cpu')
        if cpu is not None:
            args['cpu_shares'] = int(1024 * cpu)

        with docker_utils.docker_client() as docker:
            return docker.update_container(container.container_id, **args)

    @check_container_id
    def get_websocket_url(self, context, container):
        protocol = "wss" if (not CONF.docker.api_insecure and
                             CONF.docker.ca_file and
                             CONF.docker.key_file and
                             CONF.docker.cert_file) else "ws"
        version = CONF.docker.docker_remote_api_version
        remote_api_host = CONF.docker.docker_remote_api_host
        remote_api_port = CONF.docker.docker_remote_api_port
        url = protocol + "://" + remote_api_host + ":" + remote_api_port \
            + "/v" + version + "/containers/" + container.container_id \
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
            try:
                stream, stat = docker.get_archive(
                    container.container_id, path)
                if isinstance(stream, types.GeneratorType):
                    filedata = ''.encode("latin-1").join(stream)
                else:
                    filedata = stream.read()
                return filedata, stat
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    raise exception.Invalid(_("%s") % str(api_error))
                raise

    @check_container_id
    @wrap_docker_error
    def put_archive(self, context, container, path, data):
        with docker_utils.docker_client() as docker:
            try:
                docker.put_archive(container.container_id, path, data)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    raise exception.Invalid(_("%s") % str(api_error))
                raise

    @check_container_id
    @wrap_docker_error
    def stats(self, context, container):
        with docker_utils.docker_client() as docker:
            res = docker.stats(container.container_id, decode=False,
                               stream=False)

            cpu_usage = res['cpu_stats']['cpu_usage']['total_usage']
            system_cpu_usage = res['cpu_stats']['system_cpu_usage']
            cpu_percent = float(cpu_usage) / float(system_cpu_usage) * 100

            # Subtract the Cache Usage from total memory Usage
            cache_usage = 0
            if res['memory_stats'].get('stats'):
                if res['memory_stats']['stats'].get('total_inactive_file'):
                    # For Cgroup V1
                    cache_usage = res['memory_stats']['stats'].get(
                        'total_inactive_file')
                elif res['memory_stats']['stats'].get('inactive_file'):
                    # For Cgroup V2
                    cache_usage = res['memory_stats']['stats'].get(
                        'inactive_file')

            mem_usage = res['memory_stats']['usage'] - cache_usage
            mem_usage = mem_usage / 1024 / 1024
            mem_limit = res['memory_stats']['limit'] / 1024 / 1024
            mem_percent = float(mem_usage) / float(mem_limit) * 100

            blk_stats = res['blkio_stats']['io_service_bytes_recursive']
            io_read = 0
            io_write = 0
            for item in (blk_stats or []):
                if item['op'].lower() == 'read':
                    io_read = io_read + item['value']
                if item['op'].lower() == 'write':
                    io_write = io_write + item['value']

            # Note(hongbin): CNI network won't have this key
            net_stats = res.get('networks', {})
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
        return value.encode('utf-8')

    def get_container_name(self, container):
        return consts.NAME_PREFIX + container.uuid

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
                for slabel in slabels:
                    kv = slabel.split("=")
                    label = {kv[0]: kv[1]}
                    labels.update(label)
            runtimes = []
            if 'Runtimes' in info:
                for key in info['Runtimes']:
                    runtimes.append(key)
            else:
                runtimes = ['runc']
            docker_root_dir = info['DockerRootDir']

            return {'total_containers': total,
                    'running_containers': running,
                    'paused_containers': paused,
                    'stopped_containers': stopped,
                    'cpus': cpus,
                    'architecture': architecture,
                    'os_type': os_type,
                    'os': os,
                    'kernel_version': kernel_version,
                    'labels': labels,
                    'runtimes': runtimes,
                    'docker_root_dir': docker_root_dir}

    def get_total_disk_for_container(self):
        try:
            disk_usage = psutil.disk_usage(self.docker_root_dir)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            LOG.warning('Docker data root doesnot exist.')
            # give another try with system root
            disk_usage = psutil.disk_usage('/')
        total_disk = disk_usage.total / 1024 ** 3
        # TODO(hongbin): deprecate reserve_disk_for_image in flavor of
        # reserved_host_disk_mb
        return (int(total_disk),
                int(total_disk * CONF.compute.reserve_disk_for_image))

    def add_security_group(self, context, container, security_group):

        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            network_driver.add_security_groups_to_ports(container,
                                                        [security_group])

    def remove_security_group(self, context, container, security_group):

        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context=context,
                                                docker_api=docker)
            network_driver.remove_security_groups_from_ports(container,
                                                             [security_group])

    def get_available_nodes(self):
        return [self._host.get_hostname()]

    def get_available_resources(self):
        data = super(DockerDriver, self).get_available_resources()

        info = self.get_host_info()
        data['total_containers'] = info['total_containers']
        data['running_containers'] = info['running_containers']
        data['paused_containers'] = info['paused_containers']
        data['stopped_containers'] = info['stopped_containers']
        data['cpus'] = info['cpus']
        data['architecture'] = info['architecture']
        data['os_type'] = info['os_type']
        data['os'] = info['os']
        data['kernel_version'] = info['kernel_version']
        data['labels'] = info['labels']
        data['runtimes'] = info['runtimes']

        return data

    @wrap_docker_error
    def network_detach(self, context, container, network):
        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context,
                                                docker_api=docker)
            network_driver.disconnect_container_from_network(container,
                                                             network)

            # Only clear network info related to this network
            # Cannot del container.address directly which will not update
            # changed fields of the container objects as the del operate on
            # the addresses object, only base.getter will called.
            update = container.addresses
            del update[network]
            container.addresses = update
            container.save(context)

    def network_attach(self, context, container, requested_network):
        with docker_utils.docker_client() as docker:
            security_group_ids = None
            if container.security_groups:
                security_group_ids = utils.get_security_group_ids(
                    context, container.security_groups)
            network_driver = zun_network.driver(context, docker_api=docker)
            network = requested_network['network']
            if network in container.addresses:
                raise exception.ZunException('Container %(container)s has '
                                             'already connected to the '
                                             'network %(network)s.'
                                             % {'container': container.uuid,
                                                'network': network})
            network_driver.get_or_create_network(context, network)
            addrs = network_driver.connect_container_to_network(
                container, requested_network,
                security_groups=security_group_ids)
            if addrs is None:
                raise exception.ZunException(_(
                    'Unexpected missing of addresses'))
            update = {}
            update[network] = addrs
            addresses = container.addresses
            addresses.update(update)
            container.addresses = addresses
            container.save(context)

    def create_network(self, context, neutron_net_id):
        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context, docker_api=docker)
            return network_driver.create_network(neutron_net_id)

    def delete_network(self, context, network):
        with docker_utils.docker_client() as docker:
            network_driver = zun_network.driver(context,
                                                docker_api=docker)
            network_driver.remove_network(network)

    def create_capsule(self, context, capsule, image, requested_networks,
                       requested_volumes):
        capsule = self.create(context, capsule, image, requested_networks,
                              requested_volumes)
        self.start(context, capsule)
        for container in capsule.init_containers:
            self._create_container_in_capsule(context, capsule, container,
                                              requested_networks,
                                              requested_volumes)
            self._wait_for_init_container(context, container)
            container.save(context)
        for container in capsule.containers:
            self._create_container_in_capsule(context, capsule, container,
                                              requested_networks,
                                              requested_volumes)
        return capsule

    def _create_container_in_capsule(self, context, capsule, container,
                                     requested_networks, requested_volumes):
        # pull image
        image_driver_name = container.image_driver
        repo, tag = utils.parse_image_name(container.image, image_driver_name)
        image_pull_policy = utils.get_image_pull_policy(
            container.image_pull_policy, tag)
        image, image_loaded = self.pull_image(
            context, repo, tag, image_pull_policy, image_driver_name)
        image['repo'], image['tag'] = repo, tag
        if not image_loaded:
            self.load_image(image['path'])
        if image_driver_name == 'glance':
            self.read_tar_image(image)
        if image['tag'] != tag:
            LOG.warning("The input tag is different from the tag in tar")

        # create container
        with docker_utils.docker_client() as docker:
            name = container.name
            LOG.debug('Creating container with image %(image)s name %(name)s',
                      {'image': image['image'], 'name': name})
            volmaps = requested_volumes.get(container.uuid, [])
            binds = self._get_binds(context, volmaps)
            kwargs = {
                'name': self.get_container_name(container),
                'command': container.command,
                'environment': container.environment,
                'working_dir': container.workdir,
                'labels': container.labels,
                'tty': container.tty,
                'stdin_open': container.interactive,
                'entrypoint': container.entrypoint,
            }

            host_config = {}
            host_config['privileged'] = container.privileged
            host_config['binds'] = binds
            kwargs['volumes'] = [b['bind'] for b in binds.values()]
            host_config['network_mode'] = 'container:%s' % capsule.container_id
            # TODO(hongbin): Uncomment this after docker-py add support for
            # container mode for pid namespace.
            # host_config['pid_mode'] = 'container:%s' % capsule.container_id
            host_config['ipc_mode'] = 'container:%s' % capsule.container_id
            if container.auto_remove:
                host_config['auto_remove'] = container.auto_remove
            if container.memory is not None:
                host_config['mem_limit'] = str(container.memory) + 'M'
            if container.cpu is not None:
                host_config['cpu_shares'] = int(1024 * container.cpu)
            if container.restart_policy:
                count = int(container.restart_policy['MaximumRetryCount'])
                name = container.restart_policy['Name']
                host_config['restart_policy'] = {'Name': name,
                                                 'MaximumRetryCount': count}

            if container.disk:
                disk_size = str(container.disk) + 'G'
                host_config['storage_opt'] = {'size': disk_size}
            # The time unit in docker of heath checking is us, and the unit
            # of interval and timeout is seconds.
            if container.healthcheck:
                healthcheck = {}
                healthcheck['test'] = container.healthcheck.get('test', '')
                interval = container.healthcheck.get('interval', 0)
                healthcheck['interval'] = interval * 10 ** 9
                healthcheck['retries'] = int(container.healthcheck.
                                             get('retries', 0))
                timeout = container.healthcheck.get('timeout', 0)
                healthcheck['timeout'] = timeout * 10 ** 9
                kwargs['healthcheck'] = healthcheck

            kwargs['host_config'] = docker.create_host_config(**host_config)
            if image['tag']:
                image_repo = image['repo'] + ":" + image['tag']
            else:
                image_repo = image['repo']
            response = docker.create_container(image_repo, **kwargs)
            container.container_id = response['Id']
            docker.start(container.container_id)

            response = docker.inspect_container(container.container_id)
            self._populate_container(container, response, force=True)
            container.save(context)

    def _wait_for_init_container(self, context, container, timeout=3600):
        def retry_if_result_is_false(result):
            return result is False

        def check_init_container_stopped():
            status = self.show(context, container).status
            if status == consts.STOPPED:
                return True
            elif status == consts.RUNNING:
                return False
            else:
                raise exception.ZunException(
                    _("Container has unexpected status: %s") % status)

        r = tenacity.Retrying(
            stop=tenacity.stop_after_delay(timeout),
            wait=tenacity.wait_exponential(),
            retry=tenacity.retry_if_result(retry_if_result_is_false))
        r.call(check_init_container_stopped)

    def delete_capsule(self, context, capsule, force):
        merged_containers = capsule.containers + capsule.init_containers
        for container in merged_containers:
            self._delete_container_in_capsule(context, capsule, container,
                                              force)
        with docker_utils.docker_client() as docker:
            try:
                docker.stop(capsule.container_id)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    pass
        self.delete(context, capsule, force)

    def _delete_container_in_capsule(self, context, capsule, container, force):
        if not container.container_id:
            return

        with docker_utils.docker_client() as docker:
            try:
                docker.stop(container.container_id)
                docker.remove_container(container.container_id,
                                        force=force)
            except errors.APIError as api_error:
                if is_not_found(api_error):
                    return
                if is_not_connected(api_error):
                    return
                raise
