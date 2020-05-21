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

"""Handles all requests relating to compute resources (e.g. containers,
networking and storage of containers, and compute hosts on which they run)."""

from oslo_log import log as logging

from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import profiler
from zun.compute import container_actions
from zun.compute import rpcapi
import zun.conf
from zun import objects
from zun.scheduler.client import query as scheduler_client


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


@profiler.trace_cls("rpc")
class API(object):
    """API for interacting with the compute manager."""

    def __init__(self, context):
        self.rpcapi = rpcapi.API(context=context)
        self.scheduler_client = scheduler_client.SchedulerClient()
        super(API, self).__init__()

    def _record_action_start(self, context, container, action):
        objects.ContainerAction.action_start(context, container.uuid,
                                             action, want_result=False)

    def container_create(self, context, new_container, extra_spec,
                         requested_networks, requested_volumes, run,
                         pci_requests=None):
        requested_host = extra_spec.get('requested_host')
        if requested_host:
            self._validate_host(context, new_container, requested_host,
                                requested_volumes)

        try:
            host_state = self._schedule_container(context, new_container,
                                                  extra_spec)
        except exception.NoValidHost:
            new_container.status = consts.ERROR
            new_container.status_reason = _(
                "There are not enough hosts available.")
            new_container.save(context)
            return
        except Exception:
            new_container.status = consts.ERROR
            new_container.status_reason = _("Unexpected exception occurred.")
            new_container.save(context)
            raise

        # NOTE(mkrai): Intent here is to check the existence of image
        # before proceeding to create container. If image is not found,
        # container create will fail with 400 status.
        if CONF.api.enable_image_validation:
            try:
                images = self.rpcapi.image_search(
                    context, new_container.image,
                    new_container.image_driver, True, new_container.registry,
                    host_state['host'])
                if not images:
                    raise exception.ImageNotFound(image=new_container.image)
                if len(images) > 1:
                    raise exception.Conflict('Multiple images exist with same '
                                             'name. Please use the container '
                                             'uuid instead.')
            except exception.OperationNotSupported:
                LOG.info("Skip validation since search is not supported for "
                         "image '%(image)s' and image driver '%(driver)s'.",
                         {'image': new_container.image,
                          'driver': new_container.image_driver})
            except exception.ReferenceInvalidFormat:
                raise exception.InvalidValue(_("The format of image name '%s' "
                                               "is invalid.")
                                             % new_container.image)
            except Exception as e:
                LOG.warning("Skip validation since image search failed with "
                            "unexpected exception: %s", str(e))

        self._record_action_start(context, new_container,
                                  container_actions.CREATE)
        self.rpcapi.container_create(context, host_state['host'],
                                     new_container, host_state['limits'],
                                     requested_networks, requested_volumes,
                                     run, pci_requests)

    def _validate_host(self, context, container, host, requested_volumes):
        """Check whether compute nodes exist by validating the host.
        If host is supplied, we can lookup the ComputeNode in
        the API DB.

        :param context: The API request context.
        :param host: Target host.
        :param requested_volumes: the requested volumes.
        :raises: exception.RequestedHostNotFound if we find no compute nodes
                 with host and/or hypervisor_hostname.
        """

        if host:
            # When host is specified.
            try:
                objects.ComputeNode.get_by_name(context, host)
            except exception.ComputeNodeNotFound:
                LOG.info('No compute node record found for host %(host)s.',
                         {'host': host})
                container.destroy(context)
                for volmap in requested_volumes[container.uuid]:
                    try:
                        volmap._destroy_volume(context)
                    except exception.VolumeNotFound:
                        pass
                raise exception.RequestedHostNotFound(host=host)

    def _schedule_container(self, context, new_container, extra_spec):
        dests = self.scheduler_client.select_destinations(context,
                                                          [new_container],
                                                          extra_spec)
        return dests[0]

    def container_delete(self, context, container, *args):
        self._record_action_start(context, container, container_actions.DELETE)
        return self.rpcapi.container_delete(context, container, *args)

    def container_show(self, context, container):
        return self.rpcapi.container_show(context, container)

    def container_rebuild(self, context, container, run):
        self._record_action_start(context, container,
                                  container_actions.REBUILD)
        return self.rpcapi.container_rebuild(context, container, run)

    def container_reboot(self, context, container, *args):
        self._record_action_start(context, container, container_actions.REBOOT)
        return self.rpcapi.container_reboot(context, container, *args)

    def container_stop(self, context, container, *args):
        self._record_action_start(context, container, container_actions.STOP)
        return self.rpcapi.container_stop(context, container, *args)

    def container_start(self, context, container):
        self._record_action_start(context, container, container_actions.START)
        return self.rpcapi.container_start(context, container)

    def container_pause(self, context, container):
        self._record_action_start(context, container, container_actions.PAUSE)
        return self.rpcapi.container_pause(context, container)

    def container_unpause(self, context, container):
        self._record_action_start(context, container,
                                  container_actions.UNPAUSE)
        return self.rpcapi.container_unpause(context, container)

    def container_logs(self, context, container, stdout, stderr,
                       timestamps, tail, since):
        return self.rpcapi.container_logs(context, container, stdout, stderr,
                                          timestamps, tail, since)

    def container_exec(self, context, container, *args):
        data = self.rpcapi.container_exec(context, container, *args)
        token = data.pop('token', None)
        exec_id = data.get('exec_id')
        if token:
            data['proxy_url'] = '%s?token=%s&uuid=%s&exec_id=%s' % (
                CONF.websocket_proxy.base_url, token, container.uuid, exec_id)
        else:
            data['proxy_url'] = None
        return data

    def container_exec_resize(self, context, container, *args):
        return self.rpcapi.container_exec_resize(context, container, *args)

    def container_kill(self, context, container, *args):
        self._record_action_start(context, container, container_actions.KILL)
        return self.rpcapi.container_kill(context, container, *args)

    def container_update(self, context, container, *args):
        return self.rpcapi.container_update(context, container, *args)

    def container_attach(self, context, container):
        token = self.rpcapi.container_attach(context, container)
        access_url = '%s?token=%s&uuid=%s' % (
            CONF.websocket_proxy.base_url, token, container.uuid)
        return access_url

    def container_resize(self, context, container, *args):
        return self.rpcapi.container_resize(context, container, *args)

    def container_top(self, context, container, *args):
        return self.rpcapi.container_top(context, container, *args)

    def container_get_archive(self, context, container, *args):
        return self.rpcapi.container_get_archive(context, container, *args)

    def add_security_group(self, context, container, *args):
        self._record_action_start(context, container,
                                  container_actions.ADD_SECURITY_GROUP)
        return self.rpcapi.add_security_group(context, container, *args)

    def remove_security_group(self, context, container, *args):
        self._record_action_start(context, container,
                                  container_actions.REMOVE_SECURITY_GROUP)
        return self.rpcapi.remove_security_group(context, container, *args)

    def container_put_archive(self, context, container, *args):
        return self.rpcapi.container_put_archive(context, container, *args)

    def container_stats(self, context, container):
        return self.rpcapi.container_stats(context, container)

    def container_commit(self, context, container, *args):
        self._record_action_start(context, container, container_actions.COMMIT)
        return self.rpcapi.container_commit(context, container, *args)

    def image_delete(self, context, image):
        return self.rpcapi.image_delete(context, image, image.host)

    def image_pull(self, context, image):
        return self.rpcapi.image_pull(context, image, image.host)

    def image_search(self, context, image, image_driver, exact_match, *args):
        return self.rpcapi.image_search(context, image, image_driver,
                                        exact_match, *args)

    def network_detach(self, context, container, *args):
        self._record_action_start(context, container,
                                  container_actions.NETWORK_DETACH)
        return self.rpcapi.network_detach(context, container, *args)

    def network_attach(self, context, container, *args):
        self._record_action_start(context, container,
                                  container_actions.NETWORK_ATTACH)
        return self.rpcapi.network_attach(context, container, *args)

    def network_create(self, context, *args):
        return self.rpcapi.network_create(context, *args)

    def network_delete(self, context, *args):
        return self.rpcapi.network_delete(context, *args)

    def resize_container(self, context, container, *args):
        return self.rpcapi.resize_container(context, container, *args)
