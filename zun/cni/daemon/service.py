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

from concurrent import futures
import multiprocessing
import os
import threading
import time

import cotyledon
import flask
from futurist import periodics
from http import client as httplib
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from pyroute2.ipdb import transactional

from zun.cni.plugins import zun_cni_registry
from zun.cni import utils as cni_utils
from zun.common import context as zun_context
from zun.common import exception
from zun.common import utils
from zun.network import neutron
from zun import objects

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DaemonServer(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.application = flask.Flask('zun-cni-daemon')
        self.application.add_url_rule(
            '/addNetwork', methods=['POST'], view_func=self.add)
        self.application.add_url_rule(
            '/delNetwork', methods=['POST'], view_func=self.delete)
        self.headers = {'ContentType': 'application/json',
                        'Connection': 'close'}

    def _prepare_request(self):
        params = cni_utils.CNIParameters(flask.request.get_json())
        LOG.debug('Received %s request. CNI Params: %s',
                  params.CNI_COMMAND, params)
        return params

    def add(self):
        try:
            params = self._prepare_request()
        except Exception:
            LOG.exception('Exception when reading CNI params.')
            return '', httplib.BAD_REQUEST, self.headers

        try:
            vif = self.plugin.add(params)
            data = jsonutils.dumps(vif.obj_to_primitive())
        except exception.ResourceNotReady:
            LOG.error('Error when processing addNetwork request')
            return '', httplib.GATEWAY_TIMEOUT, self.headers
        except Exception:
            LOG.exception('Error when processing addNetwork request. CNI '
                          'Params: %s', params)
            return '', httplib.INTERNAL_SERVER_ERROR, self.headers

        return data, httplib.ACCEPTED, self.headers

    def delete(self):
        try:
            params = self._prepare_request()
        except Exception:
            LOG.exception('Exception when reading CNI params.')
            return '', httplib.BAD_REQUEST, self.headers

        try:
            self.plugin.delete(params)
        except exception.ResourceNotReady:
            # NOTE(dulek): It's better to ignore this error - most of the time
            #              it will happen when capsule is long gone and runtime
            #              overzealously tries to delete it from the network.
            #              We cannot really do anything without VIF metadata,
            #              so let's just tell runtime to move along.
            LOG.warning('Error when processing delNetwork request. '
                        'Ignoring this error, capsule is most likely gone')
            return '', httplib.NO_CONTENT, self.headers
        except Exception:
            LOG.exception('Error when processing delNetwork request. CNI '
                          'Params: %s.', params)
            return '', httplib.INTERNAL_SERVER_ERROR, self.headers
        return '', httplib.NO_CONTENT, self.headers

    def run(self):
        address = CONF.cni_daemon.cni_daemon_host
        port = CONF.cni_daemon.cni_daemon_port

        try:
            self.application.run(address, port, threaded=False,
                                 processes=CONF.cni_daemon.worker_num)
        except Exception:
            LOG.exception('Failed to start zun-cni-daemon.')
            raise


class CNIDaemonServerService(cotyledon.Service):
    name = "server"

    def __init__(self, worker_id, registry):
        super(CNIDaemonServerService, self).__init__(worker_id)
        self.registry = registry
        self.plugin = zun_cni_registry.ZunCNIRegistryPlugin(registry)
        self.server = DaemonServer(self.plugin)

    def run(self):
        # NOTE(dulek): We might do a *lot* of pyroute2 operations, let's
        #              make the pyroute2 timeout configurable to make sure
        #              kernel will have chance to catch up.
        transactional.SYNC_TIMEOUT = CONF.cni_daemon.pyroute2_timeout

        # Run HTTP server
        self.server.run()


class CNIDaemonWatcherService(cotyledon.Service):
    name = "watcher"

    def __init__(self, worker_id, registry):
        super(CNIDaemonWatcherService, self).__init__(worker_id)
        self.registry = registry
        self.host = CONF.host
        self.context = zun_context.get_admin_context(all_projects=True)
        self.neutron_api = neutron.NeutronAPI(self.context)
        self.periodic = periodics.PeriodicWorker.create(
            [], executor_factory=lambda: futures.ThreadPoolExecutor(
                max_workers=1))

    def run(self):
        self.periodic.add(self.sync_capsules)
        self.periodic.add(self.poll_vif_status)
        self.periodic.start()

    @periodics.periodic(spacing=60, run_immediately=True)
    def sync_capsules(self):
        LOG.debug('Start syncing capsule states.')
        capsules = objects.Capsule.list_by_host(self.context, self.host)
        capsule_in_db = set()
        for capsule in capsules:
            capsule_in_db.add(capsule.uuid)
        capsule_in_registry = self.registry.keys()
        # process capsules that are deleted
        for uuid in capsule_in_registry:
            if uuid not in capsule_in_db:
                self._on_capsule_deleted(uuid)

    def _on_capsule_deleted(self, capsule_uuid):
        try:
            # NOTE(ndesh): We need to lock here to avoid race condition
            #              with the deletion code for CNI DEL so that
            #              we delete the registry entry exactly once
            with lockutils.lock(capsule_uuid, external=True):
                if self.registry[capsule_uuid]['vif_unplugged']:
                    LOG.debug("Remove capsule %(capsule)s from registry",
                              {'capsule': capsule_uuid})
                    del self.registry[capsule_uuid]
                else:
                    LOG.debug("Received delete for capsule %(capsule)s",
                              {'capsule': capsule_uuid})
                    capsule_dict = self.registry[capsule_uuid]
                    capsule_dict['del_received'] = True
                    self.registry[capsule_uuid] = capsule_dict
        except KeyError:
            # This means someone else removed it. It's odd but safe to ignore.
            LOG.debug('Capsule %s entry already removed from registry while '
                      'handling DELETED event. Ignoring.', capsule_uuid)
            pass

    @periodics.periodic(spacing=1)
    def poll_vif_status(self):
        # get a copy of registry data stored in manager process
        registry_dict = self.registry.copy()
        inactive_vifs = {}
        for capsule_uuid in registry_dict:
            for ifname in registry_dict[capsule_uuid]['vifs']:
                vif_dict = registry_dict[capsule_uuid]['vifs'][ifname]
                if not vif_dict['active']:
                    inactive_vifs[vif_dict['id']] = ifname
        if not inactive_vifs:
            return

        LOG.debug('Checking status of vifs: %s', inactive_vifs.keys())
        # TODO(hongbin): search ports by device_owner as well
        search_opts = {'binding:host_id': self.host}
        ports = self.neutron_api.list_ports(**search_opts)['ports']
        for capsule_uuid in registry_dict:
            for port in ports:
                port_id = port['id']
                if port_id in inactive_vifs and utils.is_port_active(port):
                    ifname = inactive_vifs[port_id]
                    LOG.debug('sync status of port: %s', port_id)
                    self._update_vif_status(capsule_uuid, ifname)

    def _update_vif_status(self, capsule_uuid, ifname):
        with lockutils.lock(capsule_uuid, external=True):
            capsule_dict = self.registry.get(capsule_uuid)
            if capsule_dict:
                capsule_dict = self.registry[capsule_uuid]
                capsule_dict['vifs'][ifname]['active'] = True
                self.registry[capsule_uuid] = capsule_dict

    def terminate(self):
        if self.periodic:
            self.periodic.stop()


class CNIDaemonServiceManager(cotyledon.ServiceManager):
    def __init__(self):
        super(CNIDaemonServiceManager, self).__init__()
        # TODO(dulek): Use cotyledon.oslo_config_glue to support conf reload.
        self.manager = multiprocessing.Manager()
        registry = self.manager.dict()  # For Watcher->Server communication.
        self.add(CNIDaemonWatcherService, workers=1, args=(registry,))
        self.add(CNIDaemonServerService, workers=1, args=(registry,))
        self.register_hooks(on_terminate=self.terminate)

    def run(self):
        reaper_thread = threading.Thread(target=self._zombie_reaper,
                                         daemon=True)
        self._terminate_called = threading.Event()
        reaper_thread.start()
        super(CNIDaemonServiceManager, self).run()

    def _zombie_reaper(self):
        while True:
            try:
                res = os.waitpid(-1, os.WNOHANG)
                # don't sleep or stop if a zombie process was found
                # as there could be more
                if res != (0, 0):
                    continue
            except ChildProcessError:
                # There are no child processes yet (or they have been killed)
                pass
            except os.error:
                LOG.exception("Got OS error while reaping zombie processes")
            if self._terminate_called.isSet():
                break
            time.sleep(1)

    def terminate(self):
        self._terminate_called.set()
        self.manager.shutdown()
