# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import retrying

from os_vif import objects as obj_vif
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging

from zun.cni.binding import base as b_base
from zun.cni import utils as cni_utils
from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.network import neutron
from zun import objects


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
RETRY_DELAY = 1000  # 1 second in milliseconds
TYPE_CAPSULE = 'CAPSULE'
TYPE_CONTAINER = 'CONTAINER'


class ZunCNIRegistryPlugin(object):
    def __init__(self, registry):
        self.registry = registry
        self.host = CONF.host
        self.context = zun_context.get_admin_context(all_projects=True)
        self.neutron_api = neutron.NeutronAPI(self.context)

    def _get_container_uuid(self, params):
        # NOTE(hongbin): The runtime should set K8S_POD_NAME as
        # capsule/container uuid
        return params.args.K8S_POD_NAME

    def _get_container_type(self, params):
        return getattr(params.args, 'ZUN_CONTAINER_TYPE', TYPE_CAPSULE)

    def add(self, params):
        vifs = self._do_work(params, b_base.connect)

        container_uuid = self._get_container_uuid(params)

        # NOTE(dulek): Saving containerid to be able to distinguish old DEL
        #              requests that we should ignore. We need a lock to
        #              prevent race conditions and replace whole object in the
        #              dict for multiprocessing.Manager to notice that.
        with lockutils.lock(container_uuid, external=True):
            self.registry[container_uuid] = {
                'containerid': params.CNI_CONTAINERID,
                'vif_unplugged': False,
                'del_received': False,
                'vifs': {ifname: {'active': vif.active, 'id': vif.id}
                         for ifname, vif in vifs.items()},
            }
            LOG.debug('Saved containerid = %s for capsule/container %s',
                      params.CNI_CONTAINERID, container_uuid)

        # Wait for VIFs to become active.
        timeout = CONF.cni_daemon.vif_active_timeout

        def any_vif_inactive(vifs):
            """Return True if there is at least one VIF that's not ACTIVE."""
            return any(not vif['active'] for vif in vifs.values())

        # Wait for timeout sec, 1 sec between tries, retry when even one
        # vif is not active.
        @retrying.retry(stop_max_delay=timeout * 1000, wait_fixed=RETRY_DELAY,
                        retry_on_result=any_vif_inactive)
        def wait_for_active(container_uuid):
            return self.registry[container_uuid]['vifs']

        result = wait_for_active(container_uuid)
        for vif in result.values():
            if not vif['active']:
                LOG.error("Timed out waiting for vifs to become active")
                raise exception.ResourceNotReady(resource=container_uuid)

        return vifs[consts.DEFAULT_IFNAME]

    def delete(self, params):
        container_uuid = self._get_container_uuid(params)
        try:
            reg_ci = self.registry[container_uuid]['containerid']
            LOG.debug('Read containerid = %s for capsule/container %s',
                      reg_ci, container_uuid)
            if reg_ci and reg_ci != params.CNI_CONTAINERID:
                # NOTE(dulek): This is a DEL request for some older (probably
                #              failed) ADD call. We should ignore it or we'll
                #              unplug a running capsule/container.
                LOG.warning('Received DEL request for unknown ADD call. '
                            'Ignoring.')
                return
        except KeyError:
            pass

        try:
            self._do_work(params, b_base.disconnect)
        except exception.ContainerNotFound:
            LOG.warning('Capsule/Container is not found in DB. Ignoring.')
            pass

        # NOTE(ndesh): We need to lock here to avoid race condition
        #              with the deletion code in the watcher to ensure that
        #              we delete the registry entry exactly once
        try:
            with lockutils.lock(container_uuid, external=True):
                if self.registry[container_uuid]['del_received']:
                    LOG.debug("Remove capsule/container %(container)s from "
                              "registry", {'container': container_uuid})
                    del self.registry[container_uuid]
                else:
                    LOG.debug("unplug vif for capsule/container %(container)s",
                              {'container': container_uuid})
                    container_dict = self.registry[container_uuid]
                    container_dict['vif_unplugged'] = True
                    self.registry[container_uuid] = container_dict
        except KeyError:
            # This means the capsule/container was removed before vif was
            # unplugged. This shouldn't happen, but we can't do anything
            # about it now
            LOG.debug('Capsule/Container %s not found while handling DEL '
                      'request. Ignoring.', container_uuid)
            pass

    def _do_work(self, params, fn):
        container_uuid = self._get_container_uuid(params)
        container_type = self._get_container_type(params)

        if container_type == TYPE_CAPSULE:
            container = objects.Capsule.get_by_uuid(self.context,
                                                    container_uuid)
        elif container_type == TYPE_CONTAINER:
            container = objects.Container.get_by_uuid(self.context,
                                                      container_uuid)
        else:
            raise exception.CNIError('Unexpected type: %s' % container_type)

        vifs = cni_utils.get_vifs(container)

        for ifname, vif in vifs.items():
            is_default_gateway = (ifname == consts.DEFAULT_IFNAME)
            if is_default_gateway:
                # NOTE(ygupta): if this is the default interface, we should
                # use the ifname supplied in the CNI ADD request
                ifname = params.CNI_IFNAME

            fn(vif, self._get_inst(container), ifname, params.CNI_NETNS,
               is_default_gateway=is_default_gateway,
               container_id=params.CNI_CONTAINERID)
        return vifs

    def _get_inst(self, container):
        return obj_vif.instance_info.InstanceInfo(
            uuid=container.uuid, name=container.name)
