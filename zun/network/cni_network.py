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

import os
import shlex

from oslo_log import log as logging

from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.common import utils
import zun.conf
from zun.network import network
from zun.network import neutron
from zun.network import os_vif_util
from zun import objects

CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)

DEVICE_OWNER = 'compute:zun'

ZUN_INIT_NETWORK_READY_PATH = '/zun-init-network-ready'
ZUN_INIT = ('while ! [ -f %(file)s ] ; '
            'do sleep 1 ; done ; rm -f %(file)s ; exec '
            ) % {'file': ZUN_INIT_NETWORK_READY_PATH}


ZUN_CNI_CONF = ""
with open(CONF.cni_daemon.zun_cni_config_file, 'r') as f:
    ZUN_CNI_CONF = f.read()

PATH = os.environ['PATH']
if "CNI_PATH" in os.environ:
    PATH = os.environ['CNI_PATH'] + ':' + PATH

ZUN_CNI_BIN = "zun-cni"
ZUN_CNI_ADD_CMD = "ADD"
ZUN_CNI_DEL_CMD = "DEL"


class ZunCNI(network.Network):
    def init(self, context, docker_api):
        self.docker = docker_api
        self.neutron_api = neutron.NeutronAPI(context)
        self.context = context

    def get_or_create_network(self, *args, **kwargs):
        pass

    def create_network(self, name, neutron_net_id):
        pass

    def remove_network(self, network):
        pass

    def connect_container_to_network(self, container, requested_network,
                                     security_groups=None):
        # TODO(hongbin): implement this in zun-cni-daemon
        pass

    def disconnect_container_from_network(self, container, neutron_network_id):
        addrs_list = []
        if container.addresses and neutron_network_id:
            addrs_list = container.addresses.get(neutron_network_id, [])

        neutron_ports = set()
        all_ports = set()
        for addr in addrs_list:
            all_ports.add(addr['port'])
            if not addr['preserve_on_delete']:
                port_id = addr['port']
                neutron_ports.add(port_id)

        self.neutron_api.delete_or_unbind_ports(all_ports, neutron_ports)

    def process_networking_config(self, container, requested_network,
                                  host_config, container_kwargs, docker,
                                  security_group_ids=None):
        network_id = requested_network['network']
        addresses, port = self.neutron_api.create_or_update_port(
            container, network_id, requested_network, consts.DEVICE_OWNER_ZUN,
            security_group_ids, set_binding_host=True)
        container.addresses = {network_id: addresses}

        admin_neutron_api = neutron.NeutronAPI(zun_context.get_admin_context())
        network = admin_neutron_api.show_network(port['network_id'])['network']
        subnets = {}
        for fixed_ip in port['fixed_ips']:
            subnet_id = fixed_ip['subnet_id']
            subnets[subnet_id] = \
                admin_neutron_api.show_subnet(subnet_id)['subnet']
        vif_plugin = port.get('binding:vif_type')
        vif_obj = os_vif_util.neutron_to_osvif_vif(vif_plugin, port, network,
                                                   subnets)
        state = objects.vif.VIFState(default_vif=vif_obj)
        state_dict = state.obj_to_primitive()
        container.cni_metadata = {consts.CNI_METADATA_VIF: state_dict}
        container.save(self.context)

        host_config['network_mode'] = 'none'
        container_kwargs['mac_address'] = port['mac_address']

        # We manipulate entrypoint and command parameters in here.
        token = (container.entrypoint or []) + (container.command or [])
        new_command = ZUN_INIT + ' '.join(shlex.quote(t) for t in token)
        new_entrypoint = ['/bin/sh', '-c']
        container_kwargs['entrypoint'] = new_entrypoint
        container_kwargs['command'] = [new_command]

    def _get_env_variables(self, container, pid, cmd):
        return {
            'PATH': PATH,
            'CNI_COMMAND': cmd,
            'CNI_CONTAINERID': str(container.container_id),
            'CNI_NETNS': '/proc/%s/ns/net' % pid,
            'CNI_ARGS': "K8S_POD_NAME=%s;ZUN_CONTAINER_TYPE=CONTAINER" %
                        container.uuid,
            'CNI_IFNAME': 'eth0',
        }

    def _add(self, container, pid):
        env_variables = self._get_env_variables(container, pid,
                                                ZUN_CNI_ADD_CMD)
        utils.execute(ZUN_CNI_BIN,
                      process_input=ZUN_CNI_CONF,
                      env_variables=env_variables)

    def _delete(self, container, pid):
        env_variables = self._get_env_variables(container, pid,
                                                ZUN_CNI_DEL_CMD)
        utils.execute(ZUN_CNI_BIN,
                      process_input=ZUN_CNI_CONF,
                      env_variables=env_variables)

    def _exec_command_in_container(self, container, cmd):
        exec_id = self.docker.exec_create(container.container_id, cmd)['Id']
        output = self.docker.exec_start(exec_id)
        inspect_res = self.docker.exec_inspect(exec_id)
        return inspect_res['ExitCode'], output

    def on_container_started(self, container):
        response = self.docker.inspect_container(container.container_id)
        state = response.get('State')
        if type(state) is dict and state.get('Pid'):
            pid = state['Pid']
        else:
            pid = None
        # no change
        cni_metadata = container.cni_metadata
        if cni_metadata.get(consts.CNI_METADATA_PID) == pid:
            return

        # remove container from old network
        old_pid = cni_metadata.pop(consts.CNI_METADATA_PID, None)
        if old_pid:
            self._delete(container, old_pid)
            container.cni_metadata = cni_metadata
            container.save(self.context)
        # add container to network
        self._add(container, pid)
        cni_metadata[consts.CNI_METADATA_PID] = pid
        container.cni_metadata = cni_metadata
        container.save(self.context)

        # notify the container that network is setup
        cmd = ['touch', ZUN_INIT_NETWORK_READY_PATH]
        exit_code, output = self._exec_command_in_container(container, cmd)
        if exit_code != 0:
            raise exception.ZunException('Execute command %(cmd)s failed, '
                                         'output is: %(output)s'
                                         % {'cmd': ' '.join(cmd),
                                            'output': output})

    def on_container_stopped(self, container):
        cni_metadata = container.cni_metadata
        pid = cni_metadata.pop(consts.CNI_METADATA_PID, None)
        if pid:
            self._delete(container, pid)
            container.cni_metadata = cni_metadata
            container.save(self.context)
