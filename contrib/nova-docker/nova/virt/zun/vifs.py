# Copyright (C) 2013 VMware, Inc
# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
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

import random

import os_vif
from os_vif import exception as osv_exception
from oslo_concurrency import processutils
from oslo_log import log as logging

from nova import exception
from nova.i18n import _
from nova.network import linux_net
from nova.network import manager
from nova.network import model as network_model
from nova.network import os_vif_util
from nova import utils
from nova.virt.zun import network
from oslo_config import cfg

# We need config opts from manager, but pep8 complains, this silences it.
assert manager

CONF = cfg.CONF
CONF.import_opt('vlan_interface', 'nova.manager')
CONF.import_opt('flat_interface', 'nova.manager')

LOG = logging.getLogger(__name__)


class DockerGenericVIFDriver(object):

    def plug(self, instance, vif):
        vif_type = vif['type']

        LOG.debug('plug vif_type=%(vif_type)s instance=%(instance)s '
                  'vif=%(vif)s',
                  {'vif_type': vif_type, 'instance': instance,
                   'vif': vif})

        if vif_type is None:
            raise exception.VirtualInterfacePlugException(
                _("vif_type parameter must be present "
                  "for this vif_driver implementation"))

        # Try os-vif codepath first
        vif_obj = os_vif_util.nova_to_osvif_vif(vif)
        if vif_obj is not None:
            self._plug_os_vif(instance, vif_obj)
            return

        # Legacy non-os-vif codepath
        func = getattr(self, 'plug_%s' % vif_type, None)
        if not func:
            raise exception.VirtualInterfacePlugException(
                _("Plug vif failed because of unexpected "
                  "vif_type=%s") % vif_type)
        func(instance, vif)

    def _plug_os_vif(self, instance, vif):
        instance_info = os_vif_util.nova_to_osvif_instance(instance)

        try:
            os_vif.plug(vif, instance_info)
        except osv_exception.ExceptionBase as ex:
            msg = (_("Failure running os_vif plugin plug method: %(ex)s")
                   % {'ex': ex})
            raise exception.NovaException(msg)

    def plug_iovisor(self, instance, vif):
        """Plug docker vif into IOvisor

        Creates a port on IOvisor and onboards the interface
        """
        if_local_name = 'tap%s' % vif['id'][:11]
        if_remote_name = 'ns%s' % vif['id'][:11]

        iface_id = vif['id']
        net_id = vif['network']['id']
        tenant_id = instance['project_id']

        # Device already exists so return.
        if linux_net.device_exists(if_local_name):
            return
        undo_mgr = utils.UndoManager()

        try:
            utils.execute('ip', 'link', 'add', 'name', if_local_name, 'type',
                          'veth', 'peer', 'name', if_remote_name,
                          run_as_root=True)
            utils.execute('ifc_ctl', 'gateway', 'add_port', if_local_name,
                          run_as_root=True)
            utils.execute('ifc_ctl', 'gateway', 'ifup', if_local_name,
                          'access_vm',
                          vif['network']['label'] + "_" + iface_id,
                          vif['address'], 'pgtag2=%s' % net_id,
                          'pgtag1=%s' % tenant_id, run_as_root=True)
            utils.execute('ip', 'link', 'set', if_local_name, 'up',
                          run_as_root=True)

        except Exception:
            LOG.exception("Failed to configure network on IOvisor")
            msg = _('Failed to setup the network, rolling back')
            undo_mgr.rollback_and_reraise(msg=msg, instance=instance)

    def plug_midonet(self, instance, vif):
        """Plug into MidoNet's network port

        This accomplishes binding of the vif to a MidoNet virtual port
        """
        if_local_name = 'tap%s' % vif['id'][:11]
        if_remote_name = 'ns%s' % vif['id'][:11]
        port_id = vif['id']

        # Device already exists so return.
        if linux_net.device_exists(if_local_name):
            return

        undo_mgr = utils.UndoManager()
        try:
            utils.execute('ip', 'link', 'add', 'name', if_local_name, 'type',
                          'veth', 'peer', 'name', if_remote_name,
                          run_as_root=True)
            undo_mgr.undo_with(lambda: utils.execute(
                'ip', 'link', 'delete', if_local_name, run_as_root=True))
            utils.execute('ip', 'link', 'set', if_local_name, 'up',
                          run_as_root=True)
            utils.execute('mm-ctl', '--bind-port', port_id, if_local_name,
                          run_as_root=True)
        except Exception:
            LOG.exception("Failed to configure network")
            msg = _('Failed to setup the network, rolling back')
            undo_mgr.rollback_and_reraise(msg=msg, instance=instance)

    # We are creating our own mac's now because the linux bridge interface
    # takes on the lowest mac that is assigned to it.  By using FE range
    # mac's we prevent the interruption and possible loss of networking
    # from changing mac addresses.
    def _fe_random_mac(self):
        mac = [0xfe, 0xed,
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))

    def unplug(self, instance, vif):
        vif_type = vif['type']

        LOG.debug('vif_type=%(vif_type)s instance=%(instance)s '
                  'vif=%(vif)s',
                  {'vif_type': vif_type, 'instance': instance,
                   'vif': vif})

        if vif_type is None:
            raise exception.NovaException(
                _("vif_type parameter must be present "
                  "for this vif_driver implementation"))

        # Try os-vif codepath first
        vif_obj = os_vif_util.nova_to_osvif_vif(vif)
        if vif_obj is not None:
            self._unplug_os_vif(instance, vif_obj)
            return

        # Legacy non-os-vif codepath
        func = getattr(self, 'unplug_%s' % vif_type, None)
        if not func:
            raise exception.NovaException(
                _("Unexpected vif_type=%s") % vif_type)
        func(instance, vif)

    def _unplug_os_vif(self, instance, vif):
        instance_info = os_vif_util.nova_to_osvif_instance(instance)

        try:
            os_vif.unplug(vif, instance_info)
        except osv_exception.ExceptionBase as ex:
            msg = (_("Failure running os_vif plugin unplug method: %(ex)s")
                   % {'ex': ex})
            raise exception.NovaException(msg)

    def unplug_iovisor(self, instance, vif):
        """Unplug vif from IOvisor

        Offboard an interface and deletes port from IOvisor
        """
        if_local_name = 'tap%s' % vif['id'][:11]
        iface_id = vif['id']
        try:
            utils.execute('ifc_ctl', 'gateway', 'ifdown',
                          if_local_name, 'access_vm',
                          vif['network']['label'] + "_" + iface_id,
                          vif['address'], run_as_root=True)
            utils.execute('ifc_ctl', 'gateway', 'del_port', if_local_name,
                          run_as_root=True)
            linux_net.delete_net_dev(if_local_name)
        except processutils.ProcessExecutionError:
            LOG.exception("Failed while unplugging vif", instance=instance)

    def unplug_midonet(self, instance, vif):
        """Unplug into MidoNet's network port

        This accomplishes unbinding of the vif from its MidoNet virtual port
        """
        try:
            utils.execute('mm-ctl', '--unbind-port',
                          vif['id'], run_as_root=True)
        except processutils.ProcessExecutionError:
            LOG.exception("Failed while unplugging vif", instance=instance)

    def _create_veth_pair(self, if_local_name, if_remote_name, bridge):
        undo_mgr = utils.UndoManager()
        try:
            utils.execute('ip', 'link', 'add', 'name', if_local_name, 'type',
                          'veth', 'peer', 'name', if_remote_name,
                          run_as_root=True)
            undo_mgr.undo_with(lambda: utils.execute(
                'ip', 'link', 'delete', if_local_name, run_as_root=True))
            # NOTE(samalba): Deleting the interface will delete all
            # associated resources (remove from the bridge, its pair, etc...)
            utils.execute('ip', 'link', 'set', if_local_name, 'address',
                          self._fe_random_mac(), run_as_root=True)
            utils.execute('brctl', 'addif', bridge, if_local_name,
                          run_as_root=True)
            utils.execute('ip', 'link', 'set', if_local_name, 'up',
                          run_as_root=True)
        except Exception:
            LOG.exception("Failed to configure network")
            msg = _('Failed to setup the network, rolling back')
            undo_mgr.rollback_and_reraise(msg=msg)

    def attach(self, instance, vif, container_id):
        vif_type = vif['type']
        if_local_name = 'tap%s' % vif['id'][:11]
        if_remote_name = 'ns%s' % vif['id'][:11]
        gateways = network.find_gateways(instance, vif['network'])
        ips = network.find_fixed_ips(instance, vif['network'])

        LOG.debug('attach vif_type=%(vif_type)s instance=%(instance)s '
                  'vif=%(vif)s',
                  {'vif_type': vif_type, 'instance': instance,
                   'vif': vif})

        if not linux_net.device_exists(if_local_name):
            br_name = vif['network']['bridge']
            if (vif_type == network_model.VIF_TYPE_OVS
                    and self.ovs_hybrid_required(vif)):
                br_name = self.get_br_name(vif['id'])
            self._create_veth_pair(if_local_name, if_remote_name, br_name)

        try:
            utils.execute('ip', 'link', 'set', if_remote_name, 'netns',
                          container_id, run_as_root=True)
            utils.execute('ip', 'netns', 'exec', container_id, 'ip', 'link',
                          'set', if_remote_name, 'address', vif['address'],
                          run_as_root=True)
            for ip in ips:
                utils.execute('ip', 'netns', 'exec', container_id, 'ip',
                              'addr', 'add', ip, 'dev', if_remote_name,
                              run_as_root=True)
            utils.execute('ip', 'netns', 'exec', container_id, 'ip', 'link',
                          'set', if_remote_name, 'up', run_as_root=True)

            # Setup MTU on if_remote_name is required if it is a non
            # default value
            mtu = None
            if vif.get('mtu') is not None:
                mtu = vif.get('mtu')
            if mtu is not None:
                utils.execute('ip', 'netns', 'exec', container_id, 'ip',
                              'link', 'set', if_remote_name, 'mtu', mtu,
                              run_as_root=True)

            for gateway in gateways:
                utils.execute('ip', 'netns', 'exec', container_id,
                              'ip', 'route', 'replace', 'default', 'via',
                              gateway, 'dev', if_remote_name, run_as_root=True)

            # Disable TSO, for now no config option
            utils.execute('ip', 'netns', 'exec', container_id, 'ethtool',
                          '--offload', if_remote_name, 'tso', 'off',
                          run_as_root=True)

        except Exception:
            LOG.exception("Failed to attach vif")

    def get_br_name(self, iface_id):
        return ("qbr" + iface_id)[:network_model.NIC_NAME_LEN]

    def ovs_hybrid_required(self, vif):
        ovs_hybrid_required = self.get_firewall_required(vif) or \
            self.get_hybrid_plug_enabled(vif)
        return ovs_hybrid_required

    def get_firewall_required(self, vif):
        if vif.get('details'):
            enabled = vif['details'].get('port_filter', False)
            if enabled:
                return False
            if CONF.firewall_driver != "nova.virt.firewall.NoopFirewallDriver":
                return True
        return False

    def get_hybrid_plug_enabled(self, vif):
        if vif.get('details'):
            return vif['details'].get('ovs_hybrid_plug', False)
        return False
