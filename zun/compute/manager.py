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

import contextlib
import itertools
import math
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
from zun.compute import container_actions
import zun.conf
from zun.container import driver as driver_module
from zun.image.glance import driver as glance
from zun.network import neutron
from zun import objects
from zun.scheduler.client import report

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class Manager(periodic_task.PeriodicTasks):
    """Manages the running containers."""

    def __init__(self, container_driver=None):
        super(Manager, self).__init__(CONF)
        self.driver = driver_module.load_container_driver(container_driver)
        self.capsule_driver = driver_module.load_capsule_driver()
        self.host = CONF.host
        self._resource_tracker = None
        self.reportclient = report.SchedulerReportClient()

    def _get_driver(self, container):
        if (isinstance(container, objects.Capsule) or
                isinstance(container, objects.CapsuleContainer) or
                isinstance(container, objects.CapsuleInitContainer)):
            return self.capsule_driver
        elif isinstance(container, objects.Container):
            return self.driver
        else:
            raise exception.ZunException('Unexpected container type: %(type)s.'
                                         % {'type': type(container)})

    def restore_running_container(self, context, container, current_status):
        if (container.status == consts.RUNNING and
                current_status == consts.STOPPED):
            LOG.debug("Container %(container_uuid)s was recorded in state "
                      "(%(old_status)s) and current state is "
                      "(%(current_status)s), triggering reboot",
                      {'container_uuid': container.uuid,
                       'old_status': container.status,
                       'current_status': current_status})
            self.container_start(context, container)

    def init_containers(self, context):
        containers = objects.Container.list_by_host(context, self.host)
        # TODO(hongbin): init capsules as well
        local_containers, _ = self.driver.list(context)
        uuid_to_status_map = {container.uuid: container.status
                              for container in local_containers}
        for container in containers:
            current_status = uuid_to_status_map[container.uuid]
            self._init_container(context, container)
            if CONF.compute.remount_container_volume:
                self._remount_volume(context, container)
            if CONF.compute.resume_container_state:
                self.restore_running_container(context,
                                               container,
                                               current_status)

    def _init_container(self, context, container):
        """Initialize this container during zun-compute init."""

        if (container.status == consts.CREATING or
            container.task_state in [consts.CONTAINER_CREATING,
                                     consts.IMAGE_PULLING,
                                     consts.NETWORK_ATTACHING,
                                     consts.NETWORK_DETACHING,
                                     consts.SG_ADDING,
                                     consts.SG_REMOVING]):
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
            container.task_state = None
            self.container_delete(context, container, force=True)
            return

        if container.task_state == consts.CONTAINER_REBOOTING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying reboot request",
                      container.uuid, container.task_state)
            container.task_state = None
            self.container_reboot(context, container,
                                  CONF.docker.default_timeout)
            return

        if container.task_state == consts.CONTAINER_STOPPING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying stop request",
                      container.uuid, container.task_state)
            container.task_state = None
            self.container_stop(context, container,
                                CONF.docker.default_timeout)
            return

        if container.task_state == consts.CONTAINER_STARTING:
            LOG.debug("Container %s in transitional state %s at start-up "
                      "retrying start request",
                      container.uuid, container.task_state)
            container.task_state = None
            self.container_start(context, container)
            return

        if container.task_state == consts.CONTAINER_PAUSING:
            container.task_state = None
            self.container_pause(context, container)
            return

        if container.task_state == consts.CONTAINER_UNPAUSING:
            container.task_state = None
            self.container_unpause(context, container)
            return

        if container.task_state == consts.CONTAINER_KILLING:
            container.task_state = None
            self.container_kill(context, container)
            return

    def _remount_volume(self, context, container):
        driver = self._get_driver(container)
        volmaps = objects.VolumeMapping.list_by_container(context,
                                                          container.uuid)
        for volmap in volmaps:
            LOG.info('Re-attaching volume %(volume_id)s to %(host)s',
                     {'volume_id': volmap.cinder_volume_id,
                      'host': CONF.host})
            try:
                driver.attach_volume(context, volmap)
            except Exception as e:
                LOG.exception("Failed to re-attach volume %(volume_id)s to "
                              "container %(container_id)s: %(error)s",
                              {'volume_id': volmap.cinder_volume_id,
                               'container_id': volmap.container_uuid,
                               'error': str(e)})
                msg = _("Internal error on recovering container volume")
                self._fail_container(context, container, msg, unset_host=False)

    def _fail_container(self, context, container, error, unset_host=False):
        try:
            self._detach_volumes(context, container)
        except Exception as e:
            LOG.exception("Failed to detach volumes: %s", str(e))

        container.status = consts.ERROR
        container.status_reason = error
        if unset_host:
            container.host = None
        container.save(context)

    def _wait_for_volumes_available(
            self, context, requested_volumes, container,
            timeout=CONF.volume.timeout_wait_volume_available,
            poll_interval=1):
        driver = self._get_driver(container)
        start_time = time.time()
        try:
            volmaps = itertools.chain.from_iterable(requested_volumes.values())
            volmap = next(volmaps)
            while time.time() - start_time < timeout:
                is_available, is_error = driver.is_volume_available(
                    context, volmap)
                if is_available:
                    volmap = next(volmaps)
                if is_error:
                    break
                time.sleep(poll_interval)
        except StopIteration:
            return
        volmaps = itertools.chain.from_iterable(requested_volumes.values())
        for volmap in volmaps:
            if volmap.auto_remove:
                try:
                    driver.delete_volume(context, volmap)
                except Exception:
                    LOG.exception("Failed to delete volume")
        msg = _("Volumes did not reach available status after "
                "%d seconds") % (timeout)
        self._fail_container(context, container, msg, unset_host=True)
        raise exception.Conflict(msg)

    def _wait_for_volumes_deleted(
            self, context, volmaps, container,
            timeout=CONF.volume.timeout_wait_volume_deleted,
            poll_interval=1):
        start_time = time.time()
        try:
            volmaps = itertools.chain(volmaps)
            volmap = next(volmaps)
            while time.time() - start_time < timeout:
                if not volmap.auto_remove:
                    volmap = next(volmaps)
                driver = self._get_driver(container)
                is_deleted, is_error = driver.is_volume_deleted(
                    context, volmap)
                if is_deleted:
                    volmap = next(volmaps)
                if is_error:
                    break
                time.sleep(poll_interval)
        except StopIteration:
            return
        msg = _("Volumes cannot be successfully deleted after "
                "%d seconds") % (timeout)
        self._fail_container(context, container, msg, unset_host=True)
        raise exception.Conflict(msg)

    def _check_support_disk_quota(self, context, container):
        driver = self._get_driver(container)
        base_device_size = driver.get_host_default_base_size()
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
                container.disk = math.ceil(max(base_device_size,
                                               CONF.default_disk))
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
        if not driver.node_support_disk_quota():
            if container.disk:
                msg = _('Your host does not support disk quota feature.')
                self._fail_container(context, container, msg, unset_host=True)
                raise exception.Invalid(msg)
            LOG.warning("Ignore the configured default disk size because "
                        "the driver does not support disk quota.")
        if driver.node_support_disk_quota() and not container.disk:
            container.disk = CONF.default_disk
            return

    def container_create(self, context, limits, requested_networks,
                         requested_volumes, container, run, pci_requests=None):
        @utils.synchronized(container.uuid)
        def do_container_create():
            with utils.FinishAction(context, container_actions.CREATE,
                                    container.uuid):
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

    @contextlib.contextmanager
    def _update_task_state(self, context, container, task_state):
        if container.task_state is not None:
            LOG.debug('Skip updating container task state to %(task_state)s '
                      'because its current task state is: '
                      '%(current_task_state)s',
                      {'task_state': task_state,
                       'current_task_state': container.task_state})
            yield
            return

        container.task_state = task_state
        container.save(context)
        try:
            yield
        finally:
            container.task_state = None
            container.save(context)

    def _do_container_create_base(self, context, container, requested_networks,
                                  requested_volumes,
                                  limits=None):
        with self._update_task_state(context, container,
                                     consts.CONTAINER_CREATING):
            image_driver_name = container.image_driver
            repo, tag = utils.parse_image_name(container.image,
                                               image_driver_name,
                                               registry=container.registry)
            image_pull_policy = utils.get_image_pull_policy(
                container.image_pull_policy, tag)
            try:
                # TODO(hongbin): move image pulling logic to docker driver
                image, image_loaded = self.driver.pull_image(
                    context, repo, tag, image_pull_policy, image_driver_name,
                    registry=container.registry)
                image['repo'], image['tag'] = repo, tag
                if not image_loaded:
                    self.driver.load_image(image['path'])
            except exception.ImageNotFound as e:
                with excutils.save_and_reraise_exception():
                    LOG.error(str(e))
                    self._fail_container(context, container, str(e))
            except exception.DockerError as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("Error occurred while calling Docker image "
                              "API: %s", str(e))
                    self._fail_container(context, container, str(e))
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Unexpected exception: %s",
                                  str(e))
                    self._fail_container(context, container, str(e))

            container.image_driver = image.get('driver')
            container.save(context)
            try:
                if image['driver'] == 'glance':
                    self.driver.read_tar_image(image)
                if image['tag'] != tag:
                    LOG.warning("The input tag is different from the tag in "
                                "tar")
                if isinstance(container, objects.Capsule):
                    container = self.capsule_driver.create_capsule(
                        context, container, image, requested_networks,
                        requested_volumes)
                elif isinstance(container, objects.Container):
                    container = self.driver.create(context, container, image,
                                                   requested_networks,
                                                   requested_volumes)
                return container
            except exception.DockerError as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("Error occurred while calling Docker create "
                              "API: %s", str(e))
                    self._fail_container(context, container, str(e),
                                         unset_host=True)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Unexpected exception: %s",
                                  str(e))
                    self._fail_container(context, container, str(e),
                                         unset_host=True)

    @wrap_container_event(prefix='compute')
    def _do_container_create(self, context, container, requested_networks,
                             requested_volumes, pci_requests=None,
                             limits=None):
        LOG.debug('Creating container: %s', container.uuid)

        try:
            rt = self._get_resource_tracker()
            with rt.container_claim(context, container, pci_requests, limits):
                created_container = self._do_container_create_base(
                    context, container, requested_networks, requested_volumes,
                    limits)
                return created_container
        except exception.ResourcesUnavailable as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Container resource claim failed: %s",
                              str(e))
                self._fail_container(context, container, str(e),
                                     unset_host=True)
                self.reportclient.delete_allocation_for_container(
                    context, container.uuid)

    def _attach_volumes_for_capsule(self, context, capsule, requested_volumes):
        for c in (capsule.init_containers or []):
            self._attach_volumes(context, c, requested_volumes)
        for c in (capsule.containers or []):
            self._attach_volumes(context, c, requested_volumes)

    def _attach_volumes(self, context, container, requested_volumes):
        if isinstance(container, objects.Capsule):
            self._attach_volumes_for_capsule(context, container,
                                             requested_volumes)
            return

        try:
            volmaps = requested_volumes.get(container.uuid, [])
            for volmap in volmaps:
                volmap.container_uuid = container.uuid
                volmap.host = self.host
                volmap.create(context)
                if (volmap.connection_info and
                        (isinstance(container, objects.CapsuleContainer) or
                         isinstance(container, objects.CapsuleInitContainer))):
                    # NOTE(hongbin): In this case, the volume is already
                    # attached to this host so we don't need to do it again.
                    # This will happen only if there are multiple containers
                    # inside a capsule sharing the same volume.
                    continue
                self._attach_volume(context, container, volmap)
                self._refresh_attached_volumes(requested_volumes, volmap)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                self._fail_container(context, container, str(e),
                                     unset_host=True)

    def _attach_volume(self, context, container, volmap):
        driver = self._get_driver(container)
        context = context.elevated()
        LOG.info('Attaching volume %(volume_id)s to %(host)s',
                 {'volume_id': volmap.cinder_volume_id,
                  'host': CONF.host})
        try:
            driver.attach_volume(context, volmap)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error("Failed to attach volume %(volume_id)s to "
                          "container %(container_id)s",
                          {'volume_id': volmap.cinder_volume_id,
                           'container_id': volmap.container_uuid})
                if volmap.auto_remove:
                    try:
                        driver.delete_volume(context, volmap)
                    except Exception:
                        LOG.exception("Failed to delete volume %s.",
                                      volmap.cinder_volume_id)
                volmap.destroy()

    def _refresh_attached_volumes(self, requested_volumes, attached_volmap):
        volmaps = itertools.chain.from_iterable(requested_volumes.values())
        for volmap in volmaps:
            if volmap.volume_id != attached_volmap.volume_id:
                continue
            if (volmap.obj_attr_is_set('uuid') and
                    volmap.uuid == attached_volmap.uuid):
                continue
            volmap.volume.refresh()

    def _detach_volumes_for_capsule(self, context, capsule, reraise):
        for c in (capsule.init_containers or []):
            self._detach_volumes(context, c, reraise)
        for c in (capsule.containers or []):
            self._detach_volumes(context, c, reraise)

    def _detach_volumes(self, context, container, reraise=True):
        if isinstance(container, objects.Capsule):
            self._detach_volumes_for_capsule(context, container, reraise)
            return

        volmaps = objects.VolumeMapping.list_by_container(context,
                                                          container.uuid)
        auto_remove_volmaps = []
        for volmap in volmaps:
            db_volmaps = objects.VolumeMapping.list_by_cinder_volume(
                context, volmap.cinder_volume_id)
            self._detach_volume(context, container, volmap, reraise=reraise)
            if volmap.auto_remove and len(db_volmaps) == 1:
                self._get_driver(container).delete_volume(context, volmap)
                auto_remove_volmaps.append(volmap)
        self._wait_for_volumes_deleted(context, auto_remove_volmaps, container)

    def _detach_volume(self, context, container, volmap, reraise=True):
        if objects.VolumeMapping.count(
                context, volume_id=volmap.volume_id) == 1:
            context = context.elevated()
            try:
                self._get_driver(container).detach_volume(context, volmap)
            except Exception:
                with excutils.save_and_reraise_exception(reraise=reraise):
                    LOG.error("Failed to detach volume %(volume_id)s from "
                              "container %(container_id)s",
                              {'volume_id': volmap.cinder_volume_id,
                               'container_id': volmap.container_uuid})
        volmap.destroy()

    @wrap_container_event(prefix='compute')
    def _do_container_start(self, context, container):
        LOG.debug('Starting container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_STARTING):
            try:
                # NOTE(hongbin): capsule shouldn't reach here
                container = self.driver.start(context, container)
                container.started_at = timeutils.utcnow()
                container.save(context)
                return container
            except exception.DockerError as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("Error occurred while calling Docker start "
                              "API: %s", str(e))
                    self._fail_container(context, container, str(e))
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Unexpected exception: %s",
                                  str(e))
                    self._fail_container(context, container, str(e))

    @translate_exception
    def container_delete(self, context, container, force=False):
        @utils.synchronized(container.uuid)
        def do_container_delete():
            self._do_container_delete(context, container, force)

        utils.spawn_n(do_container_delete)

    def _do_container_delete(self, context, container, force):
        LOG.debug('Deleting container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_DELETING):
            reraise = not force
            try:
                if isinstance(container, objects.Capsule):
                    self.capsule_driver.delete_capsule(context, container,
                                                       force)
                elif isinstance(container, objects.Container):
                    self.driver.delete(context, container, force)
            except exception.DockerError as e:
                with excutils.save_and_reraise_exception(reraise=reraise):
                    LOG.error("Error occurred while calling Docker  "
                              "delete API: %s", str(e))
                    self._fail_container(context, container, str(e))
            except Exception as e:
                with excutils.save_and_reraise_exception(reraise=reraise):
                    LOG.exception("Unexpected exception: %s", str(e))
                    self._fail_container(context, container, str(e))

            self._detach_volumes(context, container, reraise=reraise)

        # Remove the claimed resource
        rt = self._get_resource_tracker()
        rt.remove_usage_from_container(context, container, True)
        self.reportclient.delete_allocation_for_container(context,
                                                          container.uuid)
        # only destroy the container in the db if the
        # delete_allocation_for_instance doesn't raise and therefore
        # allocation is successfully deleted in placement
        container.destroy(context)

    def add_security_group(self, context, container, security_group):
        @utils.synchronized(container.uuid)
        def do_add_security_group():
            self._add_security_group(context, container, security_group)

        utils.spawn_n(do_add_security_group)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.ADD_SECURITY_GROUP)
    def _add_security_group(self, context, container, security_group):
        LOG.debug('Adding security_group to container: %s', container.uuid)
        with self._update_task_state(context, container, consts.SG_ADDING):
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.add_security_group(context, container, security_group)
            container.security_groups += [security_group]
            container.save(context)

    def remove_security_group(self, context, container, security_group):
        @utils.synchronized(container.uuid)
        def do_remove_security_group():
            self._remove_security_group(context, container, security_group)

        utils.spawn_n(do_remove_security_group)

    @wrap_exception()
    @wrap_container_event(
        prefix='compute',
        finish_action=container_actions.REMOVE_SECURITY_GROUP)
    def _remove_security_group(self, context, container, security_group):
        LOG.debug('Removing security_group from container: %s', container.uuid)
        with self._update_task_state(context, container, consts.SG_REMOVING):
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.remove_security_group(context, container,
                                              security_group)
            container.security_groups = list(set(container.security_groups)
                                             - set([security_group]))
            container.save(context)

    @translate_exception
    def container_show(self, context, container):
        LOG.debug('Showing container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.show(context, container)
            if container.obj_what_changed():
                container.save(context)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker show API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.REBOOT)
    def _do_container_reboot(self, context, container, timeout):
        LOG.debug('Rebooting container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_REBOOTING):
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.reboot(context, container, timeout)
            return container

    def container_reboot(self, context, container, timeout):
        @utils.synchronized(container.uuid)
        def do_container_reboot():
            self._do_container_reboot(context, container, timeout)

        utils.spawn_n(do_container_reboot)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.STOP)
    def _do_container_stop(self, context, container, timeout):
        LOG.debug('Stopping container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_STOPPING):
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.stop(context, container, timeout)
            return container

    def container_stop(self, context, container, timeout):
        @utils.synchronized(container.uuid)
        def do_container_stop():
            self._do_container_stop(context, container, timeout)

        utils.spawn_n(do_container_stop)

    def _update_container_state(self, context, container, container_status):
        if container.status != container_status:
            container.status = container_status
            container.save(context)

    def container_rebuild(self, context, container, run):
        @utils.synchronized(container.uuid)
        def do_container_rebuild():
            self._do_container_rebuild(context, container, run)

        utils.spawn_n(do_container_rebuild)

    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.REBUILD)
    def _do_container_rebuild(self, context, container, run):
        LOG.info("start to rebuild container: %s", container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_REBUILDING):
            vol_info = {container.uuid: self._get_vol_info(context, container)}
            try:
                network_info = self._get_network_info(context, container)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self._fail_container(context, container, str(e))
            # NOTE(hongbin): capsule shouldn't reach here
            if self.driver.check_container_exist(container):
                for addr in container.addresses.values():
                    for port in addr:
                        port['preserve_on_delete'] = True

                try:
                    # NOTE(hongbin): capsule shouldn't reach here
                    self.driver.delete(context, container, True)
                except Exception as e:
                    with excutils.save_and_reraise_exception():
                        LOG.error("Rebuild container: %s failed, "
                                  "reason of failure is: %s",
                                  container.uuid,
                                  str(e))
                        self._fail_container(context, container,
                                             str(e))

            try:
                created_container = self._do_container_create_base(
                    context, container, network_info, vol_info)
                created_container.status = consts.CREATED
                created_container.status_reason = None
                created_container.save(context)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("Rebuild container:%s failed, "
                              "reason of failure is: %s", container.uuid, e)
                    self._fail_container(context, container, str(e))

            LOG.info("rebuild container: %s success", created_container.uuid)
            if run:
                self._do_container_start(context, created_container)

    def _get_vol_info(self, context, container):
        return objects.VolumeMapping.list_by_container(context,
                                                       container.uuid)

    def _get_network_info(self, context, container):
        neutron_api = neutron.NeutronAPI(context)
        network_info = []
        for network_id in container.addresses:
            try:
                addr_info = container.addresses[network_id][0]
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
            with utils.FinishAction(context, container_actions.START,
                                    container.uuid):
                self._do_container_start(context, container)

        utils.spawn_n(do_container_start)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.PAUSE)
    def _do_container_pause(self, context, container):
        LOG.debug('Pausing container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_PAUSING):
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.pause(context, container)
            return container

    def container_pause(self, context, container):
        @utils.synchronized(container.uuid)
        def do_container_pause():
            self._do_container_pause(context, container)

        utils.spawn_n(do_container_pause)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.UNPAUSE)
    def _do_container_unpause(self, context, container):
        LOG.debug('Unpausing container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_UNPAUSING):
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.unpause(context, container)
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
            # NOTE(hongbin): capsule shouldn't reach here
            return self.driver.show_logs(context, container,
                                         stdout=stdout, stderr=stderr,
                                         timestamps=timestamps, tail=tail,
                                         since=since)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker logs API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_exec(self, context, container, command, run, interactive):
        LOG.debug('Executing command in container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            exec_id = self.driver.execute_create(context, container, command,
                                                 interactive)
            if run:
                # NOTE(hongbin): capsule shouldn't reach here
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
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_exec_resize(self, context, exec_id, height, width):
        LOG.debug('Resizing the tty session used by the exec: %s', exec_id)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            return self.driver.execute_resize(exec_id, height, width)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker exec API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.KILL)
    def _do_container_kill(self, context, container, signal):
        LOG.debug('Killing a container: %s', container.uuid)
        with self._update_task_state(context, container,
                                     consts.CONTAINER_KILLING):
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.kill(context, container, signal)
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
            cpu_limit = (rt.compute_node.cpus *
                         self.driver.get_cpu_allocation_ratio())
            memory_limit = (rt.compute_node.mem_total *
                            self.driver.get_ram_allocation_ratio())
            limits = {'cpu': cpu_limit,
                      'memory': memory_limit}
            if container.cpu_policy == 'dedicated':
                limits['cpuset'] = self._get_cpuset_limits(rt.compute_node,
                                                           container)
            with rt.container_update_claim(context, container, old_container,
                                           limits):
                # NOTE(hongbin): capsule shouldn't reach here
                self.driver.update(context, container)
                container.save(context)
            return container
        except exception.ResourcesUnavailable as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Update container resource claim failed: %s",
                              str(e))
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker API: %s",
                      str(e))
            raise

    @translate_exception
    def container_attach(self, context, container):
        LOG.debug('Get websocket url from the container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            url = self.driver.get_websocket_url(context, container)
            token = uuidutils.generate_uuid()
            container.websocket_url = url
            container.websocket_token = token
            container.save(context)
            return token
        except Exception as e:
            LOG.error("Error occurred while calling "
                      "get websocket url function: %s",
                      str(e))
            raise

    @translate_exception
    def container_resize(self, context, container, height, width):
        LOG.debug('Resize tty to the container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.resize(context, container, height, width)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker "
                      "resize API: %s",
                      str(e))
            raise

    @translate_exception
    def container_top(self, context, container, ps_args):
        LOG.debug('Displaying the running processes inside the container: %s',
                  container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            return self.driver.top(context, container, ps_args)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker top API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_get_archive(self, context, container, path, encode_data):
        LOG.debug('Copying resource from the container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            filedata, stat = self.driver.get_archive(context, container, path)
            if encode_data:
                filedata = utils.encode_file_data(filedata)
            return filedata, stat
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker get_archive API: %s",
                str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_put_archive(self, context, container, path, data,
                              decode_data):
        LOG.debug('Copying resource to the container: %s', container.uuid)
        if decode_data:
            data = utils.decode_file_data(data)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            return self.driver.put_archive(context, container, path, data)
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker put_archive API: %s",
                str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_stats(self, context, container):
        LOG.debug('Displaying stats of the container: %s', container.uuid)
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            return self.driver.stats(context, container)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker stats API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", str(e))
            raise

    @translate_exception
    def container_commit(self, context, container, repository, tag=None):
        LOG.debug('Committing the container: %s', container.uuid)
        snapshot_image = None
        try:
            # NOTE(miaohb): Glance is the only driver that support image
            # uploading in the current version, so we have hard-coded here.
            # https://bugs.launchpad.net/zun/+bug/1697342
            # NOTE(hongbin): capsule shouldn't reach here
            snapshot_image = self.driver.create_image(context, repository,
                                                      glance.GlanceDriver())
        except exception.DockerError as e:
            LOG.error("Error occurred while calling glance "
                      "create_image API: %s",
                      str(e))

        @utils.synchronized(container.uuid)
        def do_container_commit():
            self._do_container_commit(context, snapshot_image, container,
                                      repository, tag)

        utils.spawn_n(do_container_commit)
        return {"uuid": snapshot_image.id}

    def _do_container_image_upload(self, context, snapshot_image,
                                   container_image_id, data, tag):
        try:
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.upload_image_data(context, snapshot_image,
                                          tag, data, glance.GlanceDriver())
        except Exception as e:
            LOG.exception("Unexpected exception while uploading image: %s",
                          str(e))
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.delete_committed_image(context, snapshot_image.id,
                                               glance.GlanceDriver())
            self.driver.delete_image(context, container_image_id,
                                     'docker')
            raise

    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.COMMIT)
    def _do_container_commit(self, context, snapshot_image, container,
                             repository, tag=None):
        container_image_id = None
        LOG.debug('Creating image...')
        if tag is None:
            tag = 'latest'

        # ensure the container is paused before doing commit
        unpause = False
        if container.status == consts.RUNNING:
            # NOTE(hongbin): capsule shouldn't reach here
            container = self.driver.pause(context, container)
            container.save(context)
            unpause = True

        try:
            # NOTE(hongbin): capsule shouldn't reach here
            container_image_id = self.driver.commit(context, container,
                                                    repository, tag)
            container_image = self.driver.get_image(repository + ':' + tag)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker commit API: %s",
                      str(e))
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.delete_committed_image(context, snapshot_image.id,
                                               glance.GlanceDriver())
            raise
        finally:
            if unpause:
                try:
                    # NOTE(hongbin): capsule shouldn't reach here
                    container = self.driver.unpause(context, container)
                    container.save(context)
                except Exception as e:
                    LOG.exception("Unexpected exception: %s", str(e))

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
        image_driver_name = CONF.default_image_driver
        repo_tag = image.repo
        if image.tag:
            repo_tag += ":" + image.tag
        if uuidutils.is_uuid_like(image.repo):
            image.tag = ''
            image_driver_name = 'glance'
        try:
            pulled_image, image_loaded = self.driver.pull_image(
                context, image.repo, image.tag, driver_name=image_driver_name)
            if not image_loaded:
                self.driver.load_image(pulled_image['path'])

            if pulled_image['driver'] == 'glance':
                self.driver.read_tar_image(pulled_image)
                if pulled_image['tag'] not in pulled_image['tags']:
                    LOG.warning("The glance image tag %(glance_tag)s is "
                                "different from %(tar_tag)s the tag in tar",
                                {'glance_tag': pulled_image['tags'],
                                 'tar_tag': pulled_image['tag']})
                repo_tag = ':'.join([pulled_image['repo'],
                                     pulled_image['tag']]) \
                    if pulled_image['tag'] else pulled_image['repo']
            image_dict = self.driver.inspect_image(repo_tag)

            image_parts = image_dict['RepoTags'][0].split(":", 1)
            image.repo = image_parts[0]
            image.tag = image_parts[1]
            image.image_id = image_dict['Id']
            image.size = image_dict['Size']
            image.save()
        except exception.ImageNotFound as e:
            LOG.error(str(e))
            return
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker image API: %s",
                      str(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s",
                          str(e))
            raise

    @translate_exception
    def image_search(self, context, image, image_driver_name, exact_match,
                     registry):
        LOG.debug('Searching image...', image=image)
        repo, tag = utils.parse_image_name(image, image_driver_name,
                                           registry=registry)
        try:
            return self.driver.search_image(context, repo, tag,
                                            image_driver_name, exact_match)
        except Exception as e:
            LOG.exception("Unexpected exception while searching image: %s",
                          str(e))
            raise

    @periodic_task.periodic_task(run_immediately=True)
    def inventory_host(self, context):
        rt = self._get_resource_tracker()
        rt.update_available_resources(context)

    def _get_cpuset_limits(self, compute_node, container):
        for numa_node in compute_node.numa_topology.nodes:
            if len(numa_node.cpuset) - len(
                    numa_node.pinned_cpus) >= container.cpu and \
                    numa_node.mem_available >= container.memory:
                return {
                    'node': numa_node.id,
                    'cpuset_cpu': numa_node.cpuset,
                    'cpuset_cpu_pinned': numa_node.pinned_cpus,
                    'cpuset_mem': numa_node.mem_available
                }
        msg = _("There may be not enough numa resources.")
        raise exception.NoValidHost(reason=msg)

    def _get_resource_tracker(self):
        if not self._resource_tracker:
            rt = compute_node_tracker.ComputeNodeTracker(
                self.host, self.driver, self.capsule_driver, self.reportclient)
            self._resource_tracker = rt
        return self._resource_tracker

    @periodic_task.periodic_task(run_immediately=True)
    def delete_unused_containers(self, context):
        """Delete container with status DELETED"""
        # NOTE(kiennt): Need to filter with both status (DELETED) and
        #               task_state (None). If task_state in
        #               [CONTAINER_DELETING] it may
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
        self.driver.update_containers_states(ctx, containers, self)
        capsules = objects.Capsule.list(ctx)
        # TODO(hongbin): use capsule driver to update capsules status
        self.driver.update_containers_states(ctx, capsules, self)

    def network_detach(self, context, container, network):
        @utils.synchronized(container.uuid)
        def do_network_detach():
            self._do_network_detach(context, container, network)

        utils.spawn_n(do_network_detach)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.NETWORK_DETACH)
    def _do_network_detach(self, context, container, network):
        LOG.debug('Detach network: %(network)s from container: %(container)s.',
                  {'container': container, 'network': network})
        with self._update_task_state(context, container,
                                     consts.NETWORK_DETACHING):
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.network_detach(context, container, network)

    def network_attach(self, context, container, requested_network):
        @utils.synchronized(container.uuid)
        def do_network_attach():
            self._do_network_attach(context, container, requested_network)

        utils.spawn_n(do_network_attach)

    @wrap_exception()
    @wrap_container_event(prefix='compute',
                          finish_action=container_actions.NETWORK_ATTACH)
    def _do_network_attach(self, context, container, requested_network):
        LOG.debug('Attach network: %(network)s to container: %(container)s.',
                  {'container': container, 'network': requested_network})
        with self._update_task_state(context, container,
                                     consts.NETWORK_ATTACHING):
            # NOTE(hongbin): capsule shouldn't reach here
            self.driver.network_attach(context, container, requested_network)

    def network_create(self, context, neutron_net_id):
        LOG.debug('Create network')
        return self.driver.create_network(context, neutron_net_id)

    def network_delete(self, context, network):
        LOG.debug('Delete network')
        self.driver.delete_network(context, network)

    def resize_container(self, context, container, patch):
        @utils.synchronized(container.uuid)
        def do_container_resize():
            self.container_update(context, container, patch)

        utils.spawn_n(do_container_resize)
