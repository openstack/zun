#    Copyright 2016 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import itertools

import six
import time

from oslo_log import log as logging
from oslo_service import periodic_task
from oslo_utils import excutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

from zun.common import consts
from zun.common import context
from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
from zun.common.utils import translate_exception
from zun.common.utils import wrap_container_event
from zun.common.utils import wrap_exception
from zun.compute import compute_node_tracker
import zun.conf
from zun.container import driver
from zun.image.glance import driver as glance
from zun.network import neutron
from zun import objects

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class Manager(periodic_task.PeriodicTasks):
    """Manages the running containers."""

    def __init__(self, container_driver=None):
        super(Manager, self).__init__(CONF)
        self.driver = driver.load_container_driver(container_driver)
        self.host = CONF.host
        self._resource_tracker = None
        if self._use_sandbox():
            self.use_sandbox = True
        else:
            self.use_sandbox = False

    def restore_running_container(self, context, container, current_status):
        if (container.status == consts.RUNNING and
                current_status == consts.STOPPED):
            LOG.debug("Container %(container_uuid)s was recorded in state "
                      "(%(old_status)s) and current state is "
                      "(%(current_status)s), triggering reboot",
                      {'container_uuid': container.uuid,
                       'old_status': container.status,
                       'current_status': current_status})
            self.container_reboot(context, container, 10)

    def init_containers(self, context):
        containers = objects.Container.list_by_host(context, self.host)
        uuid_to_status_map = {container.uuid: container.status
                              for container in self.driver.list(context)}
        for container in containers:
            current_status = uuid_to_status_map[container.uuid]
            self._init_container(context, container)
            if CONF.compute.resume_container_state:
                self.restore_running_container(context,
                                               container,
                                               current_status)

    def _init_container(self, context, container):
        """Initialize this container during zun-compute init."""

        if (container.status == consts.CREATING or
            container.task_state in [consts.CONTAINER_CREATING,
                                     consts.IMAGE_PULLING,
                                     consts.SANDBOX_CREATING]):
            LOG.debug("Container %s failed to create correctly, "
                      "setting to ERROR state", container.uuid)
            container.task_state = None
            container.status = consts.ERROR
            container.status_reason = _("Container failed to create correctly")
            container.save()
            return

        if (container.status == consts.DELETING or
                container.task_state == consts.CONTAINER_DELETING):
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying delete request",
                      container.uuid, container.task_state)
            self.container_delete(context, container, force=True)
            return

        if container.task_state == consts.CONTAINER_REBOOTING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying reboot request",
                      container.uuid, container.task_state)
            self.container_reboot(context, container,
                                  CONF.docker.default_timeout)
            return

        if container.task_state == consts.CONTAINER_STOPPING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying stop request",
                      container.uuid, container.task_state)
            self.container_stop(context, container,
                                CONF.docker.default_timeout)
            return

        if container.task_state == consts.CONTAINER_STARTING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying start request",
                      container.uuid, container.task_state)
            self.container_start(context, container)
            return

        if container.task_state == consts.CONTAINER_PAUSING:
            self.container_pause(context, container)
            return

        if container.task_state == consts.CONTAINER_UNPAUSING:
            self.container_unpause(context, container)
            return

        if container.task_state == consts.CONTAINER_KILLING:
            self.container_kill(context, container)
            return

        if container.task_state == consts.NETWORK_ATTACHING:
            self.network_attach(context, container)
            return

        if container.task_state == consts.NETWORK_DETACHING:
            self.network_detach(context, container)
            return

        if container.task_state == consts.SG_ADDING:
            self.add_security_group(context, container)
            return

        if container.task_state == consts.SG_REMOVING:
            self.remove_security_group(context, container)
            return

    def _fail_container(self, context, container, error, unset_host=False):
        try:
            self._detach_volumes(context, container)
        except Exception as e:
            LOG.exception("Failed to detach volumes: %s",
                          six.text_type(e))

        container.status = consts.ERROR
        container.status_reason = error
        container.task_state = None
        if unset_host:
            container.host = None
        container.save(context)

    def _wait_for_volumes_available(self, context, volumes, container,
                                    timeout=60, poll_interval=1):
        start_time = time.time()
        try:
            volumes = itertools.chain(volumes)
            volume = next(volumes)
            while time.time() - start_time < timeout:
                if self.driver.is_volume_available(context, volume):
                    volume = next(volumes)
                time.sleep(poll_interval)
        except StopIteration:
            return
        msg = _("Volumes did not reach available status after"
                "%d seconds") % (timeout)
        self._fail_container(context, container, msg, unset_host=True)
        raise exception.Conflict(msg)

    def _check_support_disk_quota(self, context, container):
        base_device_size = self.driver.get_host_default_base_size()
        if base_device_size:
            # NOTE(kiennt): If default_base_size is not None, it means
            #               host storage_driver is in list ['devicemapper',
            #               windowfilter', 'zfs', 'btrfs']. The following
            #               block is to prevent Zun raises Exception every time
            #               if user do not set container's disk and
            #               default_disk less than base_device_size.
            # FIXME(kiennt): This block is too complicated. We should find
            #                new efficient way to do the check.
            if not container.disk:
                container.disk = max(base_device_size, CONF.default_disk)
                return
            else:
                if container.disk < base_device_size:
                    msg = _('Disk size cannot be smaller than '
                            '%(base_device_size)s.') % {
                                'base_device_size': base_device_size
                    }
                    self._fail_container(context, container,
                                         msg, unset_host=True)
                    raise exception.Invalid(msg)
        # NOTE(kiennt): Only raise Exception when user passes disk size and
        #               the disk quota feature isn't supported in host.
        if not self.driver.node_support_disk_quota():
            if container.disk:
                msg = _('Your host does not support disk quota feature.')
                self._fail_container(context, container, msg, unset_host=True)
                raise exception.Invalid(msg)
            LOG.warning("Ignore the configured default disk size because "
                        "the driver does not support disk quota.")
        if self.driver.node_support_disk_quota() and not container.disk:
            container.disk = CONF.default_disk
            return

    def container_create(self, context, limits, requested_networks,
                         requested_volumes, container, run, pci_requests=None):
        @utils.synchronized(container.uuid)
        def do_container_create():
            self._wait_for_volumes_available(context, requested_volumes,
                                             container)
            self._attach_volumes(context, container, requested_volumes)
            self._check_support_disk_quota(context, container)
            created_container = self._do_container_create(
                context, container, requested_networks, requested_volumes,
                pci_requests, limits)
            if run:
                self._do_container_start(context, created_container)

        utils.spawn_n(do_container_create)

    def _do_sandbox_cleanup(self, context, container):
        sandbox_id = container.get_sandbox_id()
        if sandbox_id is None:
            return

        try:
            self.driver.delete_sandbox(context, container)
        except Exception as e:
            LOG.error("Error occurred while deleting sandbox: %s",
                      six.text_type(e))

    def _update_task_state(self, context, container, task_state):
        container.task_state = task_state
        container.save(context)

    def _do_container_create_base(self, context, container, requested_networks,
                                  requested_volumes, sandbox=None,
                                  limits=None):
        self._update_task_state(context, container, consts.IMAGE_PULLING)
        image_driver_name = container.image_driver
        repo, tag = utils.parse_image_name(container.image, image_driver_name)
        image_pull_policy = utils.get_image_pull_policy(
            container.image_pull_policy, tag)
        try:
            image, image_loaded = self.driver.pull_image(
                context, repo, tag, image_pull_policy, image_driver_name)
            image['repo'], image['tag'] = repo, tag
            if not image_loaded:
                self.driver.load_image(image['path'])
        except exception.ImageNotFound as e:
            with excutils.save_and_reraise_exception():
                LOG.error(six.text_type(e))
                self._do_sandbox_cleanup(context, container)
                self._fail_container(context, container, six.text_type(e))
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Error occurred while calling Docker image API: %s",
                          six.text_type(e))
                self._do_sandbox_cleanup(context, container)
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._do_sandbox_cleanup(context, container)
                self._fail_container(context, container, six.text_type(e))

        container.task_state = consts.CONTAINER_CREATING
        container.image_driver = image.get('driver')
        container.save(context)
        try:
            if image['driver'] == 'glance':
                self.driver.read_tar_image(image)
            if image['tag'] != tag:
                LOG.warning("The input tag is different from the tag in tar")
            container = self.driver.create(context, container, image,
                                           requested_networks,
                                           requested_volumes)
            self._update_task_state(context, container, None)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Error occurred while calling Docker create API: %s",
                          six.text_type(e))
                self._do_sandbox_cleanup(context, container)
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._do_sandbox_cleanup(context, container)
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)

    @wrap_container_event(prefix='compute')
    def _do_container_create(self, context, container, requested_networks,
                             requested_volumes, pci_requests=None,
                             limits=None):
        LOG.debug('Creating container: %s', container.uuid)

        try:
            rt = self._get_resource_tracker()
            # As sriov port also need to claim, we need claim pci port before
            # create sandbox.
            with rt.container_claim(context, container, pci_requests, limits):
                sandbox = None
                if self.use_sandbox:
                    sandbox = self._create_sandbox(context, container,
                                                   requested_networks)

                created_container = self._do_container_create_base(
                    context, container, requested_networks, requested_volumes,
                    sandbox, limits)
                return created_container
        except exception.ResourcesUnavailable as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Container resource claim failed: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)

    def _attach_volumes(self, context, container, volumes):
        try:
            for volume in volumes:
                volume.container_uuid = container.uuid
                self._attach_volume(context, volume)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)

    def _attach_volume(self, context, volume):
        volume.create(context)
        context = context.elevated()
        LOG.info('Attaching volume %(volume_id)s to %(host)s',
                 {'volume_id': volume.volume_id,
                  'host': CONF.host})
        try:
            self.driver.attach_volume(context, volume)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error("Failed to attach volume %(volume_id)s to "
                          "container %(container_id)s",
                          {'volume_id': volume.volume_id,
                           'container_id': volume.container_uuid})
                volume.destroy()

    def _detach_volumes(self, context, container, reraise=True):
        volumes = objects.VolumeMapping.list_by_container(context,
                                                          container.uuid)
        for volume in volumes:
            self._detach_volume(context, volume, reraise=reraise)
            if volume.auto_remove:
                self.driver.delete_volume(context, volume)

    def _detach_volume(self, context, volume, reraise=True):
        context = context.elevated()
        try:
            self.driver.detach_volume(context, volume)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Failed to detach volume %(volume_id)s from "
                          "container %(container_id)s",
                          {'volume_id': volume.volume_id,
                           'container_id': volume.container_uuid})
        volume.destroy()

    def _use_sandbox(self):
        if CONF.use_sandbox and self.driver.capabilities["support_sandbox"]:
            return True
        elif (not CONF.use_sandbox and
                self.driver.capabilities["support_standalone"]):
            return False
        else:
            raise exception.ZunException(_(
                "The configuration of use_sandbox '%(use_sandbox)s' is not "
                "supported by driver '%(driver)s'.") %
                {'use_sandbox': CONF.use_sandbox,
                 'driver': self.driver})

    def _create_sandbox(self, context, container, requested_networks):
        self._update_task_state(context, container, consts.SANDBOX_CREATING)
        sandbox_image = CONF.sandbox_image
        sandbox_image_driver = CONF.sandbox_image_driver
        sandbox_image_pull_policy = CONF.sandbox_image_pull_policy
        repo, tag = utils.parse_image_name(sandbox_image,
                                           sandbox_image_driver)
        try:
            image, image_loaded = self.driver.pull_image(
                context, repo, tag, sandbox_image_pull_policy,
                sandbox_image_driver)
            if not image_loaded:
                self.driver.load_image(image['path'])
            sandbox_id = self.driver.create_sandbox(
                context, container, image=sandbox_image,
                requested_networks=requested_networks,
                requested_volumes=[])
            return sandbox_id
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    @wrap_container_event(prefix='compute')
    def _do_container_start(self, context, container):
        LOG.debug('Starting container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_STARTING)
        try:
            container = self.driver.start(context, container)
            self._update_task_state(context, container, None)
            container.started_at = timeutils.utcnow()
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Error occurred while calling Docker start API: %s",
                          six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    @translate_exception
    def container_delete(self, context, container, force=False):
        @utils.synchronized(container.uuid)
        def do_container_delete():
            self._do_container_delete(context, container, force)

        utils.spawn_n(do_container_delete)

    def _do_container_delete(self, context, container, force):
        LOG.debug('Deleting container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_DELETING)
        reraise = not force
        try:
            self.driver.delete(context, container, force)
            if self.use_sandbox:
                self._delete_sandbox(context, container, reraise)
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker  "
                          "delete API: %s", six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s", six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

        self._detach_volumes(context, container, reraise=reraise)

        self._update_task_state(context, container, None)
        container.destroy(context)
        self._get_resource_tracker()

        # Remove the claimed resource
        rt = self._get_resource_tracker()
        rt.remove_usage_from_container(context, container, True)

    def _delete_sandbox(self, context, container, reraise=False):
        sandbox_id = container.get_sandbox_id()
        if sandbox_id:
            self._update_task_state(context, container,
                                    consts.SANDBOX_DELETING)
            try:
                self.driver.delete_sandbox(context, container)
            except Exception as e:
                with excutils.save_and_reraise_exception(reraise=reraise):
                    LOG.exception("Unexpected exception: %s", six.text_type(e))
                    self._fail_container(context, container, six.text_type(e))

    def add_security_group(self, context, container, security_group):
        @utils.synchronized(container.uuid)
        def do_add_security_group():
            self._add_security_group(context, container, security_group)

        utils.spawn_n(do_add_security_group)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _add_security_group(self, context, container, security_group):
        LOG.debug('Adding security_group to container: %s', container.uuid)
        self._update_task_state(context, container, consts.SG_ADDING)
        self.driver.add_security_group(context, container, security_group)
        self._update_task_state(context, container, None)
        container.security_groups += [security_group]
        container.save(context)

    def remove_security_group(self, context, container, security_group):
        @utils.synchronized(container.uuid)
        def do_remove_security_group():
            self._remove_security_group(context, container, security_group)

        utils.spawn_n(do_remove_security_group)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _remove_security_group(self, context, container, security_group):
        LOG.debug('Removing security_group from container: %s', container.uuid)
        self._update_task_state(context, container, consts.SG_REMOVING)
        self.driver.remove_security_group(context, container,
                                          security_group)
        self._update_task_state(context, container, None)
        security_groups = (set(container.security_groups)
                           - set([security_group]))
        container.security_groups = list(security_groups)
        container.save(context)

    @translate_exception
    def container_show(self, context, container):
        LOG.debug('Showing container: %s', container.uuid)
        try:
            container = self.driver.show(context, container)
            if container.obj_what_changed():
                container.save(context)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker show API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_container_reboot(self, context, container, timeout):
        LOG.debug('Rebooting container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_REBOOTING)
        container = self.driver.reboot(context, container, timeout)
        self._update_task_state(context, container, None)
        return container

    def container_reboot(self, context, container, timeout):
        @utils.synchronized(container.uuid)
        def do_container_reboot():
            self._do_container_reboot(context, container, timeout)

        utils.spawn_n(do_container_reboot)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_container_stop(self, context, container, timeout):
        LOG.debug('Stopping container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_STOPPING)
        container = self.driver.stop(context, container, timeout)
        self._update_task_state(context, container, None)
        return container

    def container_stop(self, context, container, timeout):
        @utils.synchronized(container.uuid)
        def do_container_stop():
            self._do_container_stop(context, container, timeout)

        utils.spawn_n(do_container_stop)

    def _update_container_state(self, context, container, container_status):
        container.status = container_status
        container.save(context)

    def container_rebuild(self, context, container):
        @utils.synchronized(container.uuid)
        def do_container_rebuild():
            self._do_container_rebuild(context, container)

        utils.spawn_n(do_container_rebuild)

    @wrap_container_event(prefix='compute')
    def _do_container_rebuild(self, context, container):
        LOG.info("start to rebuild container: %s", container.uuid)
        ori_status = container.status
        vol_info = self._get_vol_info(context, container)
        try:
            network_info = self._get_network_info(context, container)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                self._fail_container(context, container, six.text_type(e))
        self._update_container_state(context, container, consts.REBUILDING)
        if self.driver.check_container_exist(container):
            for addr in container.addresses.values():
                for port in addr:
                    port['preserve_on_delete'] = True

            try:
                self._update_task_state(context, container,
                                        consts.CONTAINER_DELETING)
                self.driver.delete(context, container, True)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("Rebuild container: %s failed, "
                              "reason of failure is: %s",
                              container.uuid,
                              six.text_type(e))
                    self._fail_container(context, container, six.text_type(e))

        try:
            self._update_task_state(context, container,
                                    consts.CONTAINER_CREATING)
            created_container = self._do_container_create_base(
                context, container, network_info, vol_info)
            self._update_container_state(context, container, consts.CREATED)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Rebuild container:%s failed, "
                          "reason of failure is: %s", container.uuid, e)
        LOG.info("rebuild container: %s success", created_container.uuid)
        if ori_status == consts.RUNNING:
            self._do_container_start(context, created_container)
        return

    def _get_vol_info(self, context, container):
        volumes = objects.VolumeMapping.list_by_container(context,
                                                          container.uuid)
        return volumes

    def _get_network_info(self, context, container):
        neutron_api = neutron.NeutronAPI(context)
        network_info = []
        for i in range(len(container.addresses)):
            try:
                network_id = container.addresses.keys()[i]
                addr_info = container.addresses.values()[i][0]
                port_id = addr_info.get('port')
                neutron_api.get_neutron_port(port_id)
                network = neutron_api.get_neutron_network(network_id)
            except exception.PortNotFound:
                LOG.exception("The port: %s used by the source container "
                              "does not exist, can not rebuild", port_id)
                raise
            except exception.NetworkNotFound:
                LOG.exception("The network: %s used by the source container "
                              "does not exist, can not rebuild", network_id)
                raise
            except Exception as e:
                LOG.exception("Unexpected exception: %s", e)
                raise
            preserve_info = addr_info.get('preserve_on_delete')
            network_info.append({'network': network_id,
                                 'port': port_id,
                                 'router:external':
                                     network.get('router:external'),
                                 'shared': network.get('shared'),
                                 'fixed_ip': '',
                                 'preserve_on_delete': preserve_info})
        return network_info

    def container_start(self, context, container):
        @utils.synchronized(container.uuid)
        def do_container_start():
            self._do_container_start(context, container)

        utils.spawn_n(do_container_start)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_container_pause(self, context, container):
        LOG.debug('Pausing container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_PAUSING)
        container = self.driver.pause(context, container)
        self._update_task_state(context, container, None)
        container.save(context)
        return container

    def container_pause(self, context, container):
        @utils.synchronized(container.uuid)
        def do_container_pause():
            self._do_container_pause(context, container)

        utils.spawn_n(do_container_pause)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_container_unpause(self, context, container):
        LOG.debug('Unpausing container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_UNPAUSING)
        container = self.driver.unpause(context, container)
        self._update_task_state(context, container, None)
        container.save(context)
        return container

    def container_unpause(self, context, container):
        @utils.synchronized(container.uuid)
        def do_container_unpause():
            self._do_container_unpause(context, container)

        utils.spawn_n(do_container_unpause)

    @translate_exception
    def container_logs(self, context, container, stdout, stderr,
                       timestamps, tail, since):
        LOG.debug('Showing container logs: %s', container.uuid)
        try:
            return self.driver.show_logs(context, container,
                                         stdout=stdout, stderr=stderr,
                                         timestamps=timestamps, tail=tail,
                                         since=since)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker logs API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_exec(self, context, container, command, run, interactive):
        LOG.debug('Executing command in container: %s', container.uuid)
        try:
            exec_id = self.driver.execute_create(context, container, command,
                                                 interactive)
            if run:
                output, exit_code = self.driver.execute_run(exec_id, command)
                return {"output": output,
                        "exit_code": exit_code,
                        "exec_id": None,
                        "token": None}
            else:
                token = uuidutils.generate_uuid()
                url = CONF.docker.docker_remote_api_url
                exec_instace = objects.ExecInstance(
                    context, container_id=container.id, exec_id=exec_id,
                    url=url, token=token)
                exec_instace.create(context)
                return {'output': None,
                        'exit_code': None,
                        'exec_id': exec_id,
                        'token': token}
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker exec API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_exec_resize(self, context, exec_id, height, width):
        LOG.debug('Resizing the tty session used by the exec: %s', exec_id)
        try:
            return self.driver.execute_resize(exec_id, height, width)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker exec API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_container_kill(self, context, container, signal):
        LOG.debug('Killing a container: %s', container.uuid)
        self._update_task_state(context, container, consts.CONTAINER_KILLING)
        container = self.driver.kill(context, container, signal)
        self._update_task_state(context, container, None)
        container.save(context)
        return container

    def container_kill(self, context, container, signal):
        @utils.synchronized(container.uuid)
        def do_container_kill():
            self._do_container_kill(context, container, signal)

        utils.spawn_n(do_container_kill)

    @translate_exception
    def container_update(self, context, container, patch):
        LOG.debug('Updating a container: %s', container.uuid)
        old_container = container.obj_clone()
        # Update only the fields that have changed
        for field, patch_val in patch.items():
            if getattr(container, field) != patch_val:
                setattr(container, field, patch_val)

        try:
            rt = self._get_resource_tracker()
            # TODO(hongbin): limits should be populated by scheduler
            # FIXME(hongbin): rt.compute_node could be None
            limits = {'cpu': rt.compute_node.cpus,
                      'memory': rt.compute_node.mem_total}
            with rt.container_update_claim(context, container, old_container,
                                           limits):
                self.driver.update(context, container)
                container.save(context)
            return container
        except exception.ResourcesUnavailable as e:
            raise exception.Conflict(six.text_type(e))
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker API: %s",
                      six.text_type(e))
            raise

    @translate_exception
    def container_attach(self, context, container):
        LOG.debug('Get websocket url from the container: %s', container.uuid)
        try:
            url = self.driver.get_websocket_url(context, container)
            token = uuidutils.generate_uuid()
            container.websocket_url = url
            container.websocket_token = token
            container.save(context)
            return token
        except Exception as e:
            LOG.error("Error occurred while calling "
                      "get websocket url function: %s",
                      six.text_type(e))
            raise

    @translate_exception
    def container_resize(self, context, container, height, width):
        LOG.debug('Resize tty to the container: %s', container.uuid)
        try:
            container = self.driver.resize(context, container, height, width)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker "
                      "resize API: %s",
                      six.text_type(e))
            raise

    @translate_exception
    def container_top(self, context, container, ps_args):
        LOG.debug('Displaying the running processes inside the container: %s',
                  container.uuid)
        try:
            return self.driver.top(context, container, ps_args)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker top API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_get_archive(self, context, container, path):
        LOG.debug('Copying resource from the container: %s', container.uuid)
        try:
            return self.driver.get_archive(context, container, path)
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker get_archive API: %s",
                six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_put_archive(self, context, container, path, data):
        LOG.debug('Copying resource to the container: %s', container.uuid)
        try:
            return self.driver.put_archive(context, container, path, data)
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker put_archive API: %s",
                six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_stats(self, context, container):
        LOG.debug('Displaying stats of the container: %s', container.uuid)
        try:
            return self.driver.stats(context, container)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker stats API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_commit(self, context, container, repository, tag=None):
        LOG.debug('Committing the container: %s', container.uuid)
        snapshot_image = None
        try:
            # NOTE(miaohb): Glance is the only driver that support image
            # uploading in the current version, so we have hard-coded here.
            # https://bugs.launchpad.net/zun/+bug/1697342
            snapshot_image = self.driver.create_image(context, repository,
                                                      glance.GlanceDriver())
        except exception.DockerError as e:
            LOG.error("Error occurred while calling glance "
                      "create_image API: %s",
                      six.text_type(e))

        @utils.synchronized(container.uuid)
        def do_container_commit():
            self._do_container_commit(context, snapshot_image, container,
                                      repository, tag)

        utils.spawn_n(do_container_commit)
        return {"uuid": snapshot_image.id}

    def _do_container_image_upload(self, context, snapshot_image,
                                   container_image_id, data, tag):
        try:
            self.driver.upload_image_data(context, snapshot_image,
                                          tag, data, glance.GlanceDriver())
        except Exception as e:
            LOG.exception("Unexpected exception while uploading image: %s",
                          six.text_type(e))
            self.driver.delete_committed_image(context, snapshot_image.id,
                                               glance.GlanceDriver())
            self.driver.delete_image(context, container_image_id,
                                     'docker')
            raise

    @wrap_container_event(prefix='compute')
    def _do_container_commit(self, context, snapshot_image, container,
                             repository, tag=None):
        container_image_id = None
        LOG.debug('Creating image...')
        if tag is None:
            tag = 'latest'

        # ensure the container is paused before doing commit
        unpause = False
        if container.status == consts.RUNNING:
            container = self.driver.pause(context, container)
            container.save(context)
            unpause = True

        try:
            container_image_id = self.driver.commit(context, container,
                                                    repository, tag)
            container_image = self.driver.get_image(repository + ':' + tag)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker commit API: %s",
                      six.text_type(e))
            self.driver.delete_committed_image(context, snapshot_image.id,
                                               glance.GlanceDriver())
            raise
        finally:
            if unpause:
                try:
                    container = self.driver.unpause(context, container)
                    container.save(context)
                except Exception as e:
                    LOG.exception("Unexpected exception: %s", six.text_type(e))

        LOG.debug('Upload image %s to glance', container_image_id)
        self._do_container_image_upload(context, snapshot_image,
                                        container_image_id,
                                        container_image, tag)

    def image_delete(self, context, image):
        utils.spawn_n(self._do_image_delete, context, image)

    def _do_image_delete(self, context, image):
        LOG.debug('Deleting image...')
        # TODO(hongbin): Let caller pass down image_driver instead of using
        # CONF.default_image_driver
        if image.image_id:
            self.driver.delete_image(context, image.image_id)
        image.destroy(context, image.uuid)

    def image_pull(self, context, image):
        utils.spawn_n(self._do_image_pull, context, image)

    def _do_image_pull(self, context, image):
        LOG.debug('Creating image...')
        repo_tag = image.repo
        if image.tag:
            repo_tag += ":" + image.tag
        try:
            pulled_image, image_loaded = self.driver.pull_image(
                context, image.repo, image.tag)
            if not image_loaded:
                self.driver.load_image(pulled_image['path'])
            image_dict = self.driver.inspect_image(repo_tag)
            image.image_id = image_dict['Id']
            image.size = image_dict['Size']
            image.save()
        except exception.ImageNotFound as e:
            LOG.error(six.text_type(e))
            return
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker image API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s",
                          six.text_type(e))
            raise

    @translate_exception
    def image_search(self, context, image, image_driver_name, exact_match):
        LOG.debug('Searching image...', image=image)
        repo, tag = utils.parse_image_name(image, image_driver_name)
        try:
            return self.driver.search_image(context, repo, tag,
                                            image_driver_name, exact_match)
        except Exception as e:
            LOG.exception("Unexpected exception while searching image: %s",
                          six.text_type(e))
            raise

    @periodic_task.periodic_task(run_immediately=True)
    def inventory_host(self, context):
        rt = self._get_resource_tracker()
        rt.update_available_resources(context)

    def _get_resource_tracker(self):
        if not self._resource_tracker:
            rt = compute_node_tracker.ComputeNodeTracker(self.host,
                                                         self.driver)
            self._resource_tracker = rt
        return self._resource_tracker

    @periodic_task.periodic_task(run_immediately=True)
    def delete_unused_containers(self, context):
        """Delete container with status DELETED"""
        # NOTE(kiennt): Need to filter with both status (DELETED) and
        #               task_state (None). If task_state in
        #               [CONTAINER_DELETING, SANDBOX_DELETING] it may
        #               raise some errors when try to delete container.
        filters = {
            'auto_remove': True,
            'status': consts.DELETED,
            'task_state': None,
        }
        containers = objects.Container.list(context,
                                            filters=filters)

        if containers:
            for container in containers:
                try:
                    msg = ('%(behavior)s deleting container '
                           '%(container_name)s with status DELETED')
                    LOG.info(msg, {'behavior': 'Start',
                                   'container_name': container.name})
                    self.container_delete(context, container, True)
                    LOG.info(msg, {'behavior': 'Complete',
                                   'container_name': container.name})
                except exception.DockerError:
                    return
                except Exception:
                    return

    @periodic_task.periodic_task(spacing=CONF.sync_container_state_interval,
                                 run_immediately=True)
    @context.set_context
    def sync_container_state(self, ctx):
        LOG.debug('Start syncing container states.')

        containers = objects.Container.list(ctx)
        self.driver.update_containers_states(ctx, containers)
        capsules = objects.Capsule.list(ctx)
        for capsule in capsules:
            container = objects.Container.get_by_uuid(
                ctx, capsule.containers_uuids[1])
            if capsule.host != container.host:
                capsule.host = container.host
                capsule.save(ctx)
        LOG.debug('Complete syncing container states.')

    def capsule_create(self, context, capsule, requested_networks,
                       requested_volumes, limits):
        @utils.synchronized("capsule-" + capsule.uuid)
        def do_capsule_create():
            self._do_capsule_create(context, capsule, requested_networks,
                                    requested_volumes, limits)

        utils.spawn_n(do_capsule_create)

    def _do_capsule_create(self, context, capsule,
                           requested_networks=None,
                           requested_volumes=None,
                           limits=None):
        """Create capsule in the compute node

        :param context: security context
        :param capsule: the special capsule object
        :param requested_networks: the network ports that capsule will
               connect
        :param requested_volumes: the volume that capsule need
        :param limits: no use field now.
        """
        # NOTE(kevinz): Here create the sandbox container for the
        # first function container --> capsule.containers[1].
        # capsule.containers[0] will only be used as recording the
        # the sandbox_container info, and the sandbox_id of this contianer
        # is itself.
        sandbox = self._create_sandbox(context,
                                       capsule.containers[0],
                                       requested_networks)
        sandbox_id = capsule.containers[0].get_sandbox_id()
        capsule.containers[0].task_state = None
        capsule.containers[0].status = consts.RUNNING
        capsule.containers[0].container_id = sandbox_id
        capsule.containers[0].set_sandbox_id(sandbox_id)
        capsule.containers[0].save(context)
        capsule.addresses = capsule.containers[0].addresses
        capsule.save(context)

        for container in capsule.containers[1:]:
            container_requested_volumes = []
            container.set_sandbox_id(sandbox_id)
            container.addresses = capsule.containers[0].addresses
            container_name = container.name
            for volume in requested_volumes:
                if volume.get(container_name, None):
                    container_requested_volumes.append(
                        volume.get(container_name))
            self._attach_volumes(context, container,
                                 container_requested_volumes)
            # Make sure the sandbox_id is set into meta. If not,
            # when container delete, it will delete container network
            # without considering sandbox.
            container.save(context)
            # Add volume assignment
            created_container = \
                self._do_container_create_base(context,
                                               container,
                                               requested_networks,
                                               container_requested_volumes,
                                               sandbox=sandbox,
                                               limits=limits)
            self._do_container_start(context, created_container)

            # Save the volumes_info to capsule database
            for volumeapp in container_requested_volumes:
                volume_id = volumeapp.volume_id
                container_uuid = volumeapp.container_uuid
                if capsule.volumes_info:
                    container_attached = capsule.volumes_info.get(volume_id)
                else:
                    capsule.volumes_info = {}
                    container_attached = None
                if container_attached:
                    if container_uuid not in container_attached:
                        container_attached.append(container_uuid)
                else:
                    container_list = [container_uuid]
                    capsule.volumes_info[volume_id] = container_list

        capsule.status = consts.RUNNING
        capsule.save(context)

    def capsule_delete(self, context, capsule):
        # NOTE(kevinz): Delete functional containers first and then delete
        # sandbox container
        for uuid in capsule.containers_uuids[1:]:
            try:
                container = \
                    objects.Container.get_by_uuid(context, uuid)
                self._do_container_delete(context, container, force=True)
            except Exception as e:
                LOG.exception("Failed to delete container %(uuid0)s because "
                              "it doesn't exist in the capsule. Stale data "
                              "identified by %(uuid1)s is deleted from "
                              "database: %(error)s",
                              {'uuid0': uuid, 'uuid1': uuid, 'error': e})
        try:
            if capsule.containers_uuids:
                container = \
                    objects.Container.get_by_uuid(context,
                                                  capsule.containers_uuids[0])
                self._delete_sandbox(context, container, reraise=False)
                self._do_container_delete(context, container, force=True)
        except Exception as e:
            LOG.exception(e)
        capsule.task_state = None
        capsule.save(context)
        capsule.destroy(context)

    def network_detach(self, context, container, network):
        @utils.synchronized(container.uuid)
        def do_network_detach():
            self._do_network_detach(context, container, network)

        utils.spawn_n(do_network_detach)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_network_detach(self, context, container, network):
        LOG.debug('Detach network: %(network)s from container: %(container)s.',
                  {'container': container, 'network': network})
        self._update_task_state(context, container,
                                consts.NETWORK_DETACHING)
        self.driver.network_detach(context, container, network)
        self._update_task_state(context, container, None)

    def network_attach(self, context, container, requested_network):
        @utils.synchronized(container.uuid)
        def do_network_attach():
            self._do_network_attach(context, container, requested_network)

        utils.spawn_n(do_network_attach)

    @wrap_exception()
    @wrap_container_event(prefix='compute')
    def _do_network_attach(self, context, container, requested_network):
        LOG.debug('Attach network: %(network)s to container: %(container)s.',
                  {'container': container, 'network': requested_network})
        self._update_task_state(context, container,
                                consts.NETWORK_ATTACHING)
        self.driver.network_attach(context, container, requested_network)
        self._update_task_state(context, container, None)

    def network_create(self, context, network):
        LOG.debug('Create network')
        docker_network = self.driver.create_network(context, network)
        network.network_id = docker_network['Id']
        network.save()

    def resize_container(self, context, container, patch):
        @utils.synchronized(container.uuid)
        def do_container_resize():
            self.container_update(context, container, patch)

        utils.spawn_n(do_container_resize)
