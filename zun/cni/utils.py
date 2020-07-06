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

from os_vif.objects import base
from oslo_config import cfg
from oslo_log import log as logging

from zun.common import consts


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def get_vifs(container):
    try:
        cni_metadata = container.cni_metadata
        vif_state = cni_metadata[consts.CNI_METADATA_VIF]
    except KeyError:
        return {}
    vif_state = base.VersionedObject.obj_from_primitive(vif_state)
    vifs_dict = vif_state.vifs
    LOG.debug("Got VIFs from cni_metadata: %r", vifs_dict)
    return vifs_dict


def convert_netns(netns):
    """Convert /proc based netns path to Docker-friendly path.

    When CONF.docker_mode is set this method will change /proc to
    /CONF.cni_daemon.cni_daemon.netns_proc_dir. This allows netns manipulations
    to work when running in Docker container on Zun host.

    :param netns: netns path to convert.
    :return: Converted netns path.
    """
    if CONF.cni_daemon.docker_mode:
        return netns.replace('/proc', CONF.cni_daemon.netns_proc_dir)
    else:
        return netns


def _osvif_route_to_dict(route):
    return {
        'gateway': str(route.gateway),
        'cidr': str(route.cidr),
    }


def _osvif_fip_to_dict(fix):
    return {
        'address': str(fix.address),
    }


def _osvif_subnet_to_dict(subnet):
    subnet_dict = {
        'routes': [_osvif_route_to_dict(r)
                   for r in subnet.routes.objects],
        'ips': [_osvif_fip_to_dict(ip) for ip in subnet.ips],
        'cidr': {
            'version': subnet.cidr.version,
            'prefixlen': subnet.cidr.prefixlen,
        },
    }
    if subnet.obj_attr_is_set('gateway'):
        subnet_dict['gateway'] = str(subnet.gateway)
    return subnet_dict


def _osvif_network_to_dict(network):
    return {
        'subnets': [_osvif_subnet_to_dict(s)
                    for s in network.subnets.objects],
        'mtu': network.mtu,
    }


def osvif_vif_to_dict(vif):
    return {
        'network': _osvif_network_to_dict(vif.network),
        'vif_name': vif.vif_name,
        'address': str(vif.address),
        'bridge_name': vif.bridge_name,
    }


class CNIConfig(dict):
    def __init__(self, cfg):
        super(CNIConfig, self).__init__(cfg)

        for k, v in self.items():
            if not k.startswith('_'):
                setattr(self, k, v)


class CNIArgs(object):
    def __init__(self, value):
        for item in value.split(';'):
            k, v = item.split('=', 1)
            if not k.startswith('_'):
                setattr(self, k, v)


class CNIParameters(object):
    def __init__(self, env, cfg=None):
        for k, v in env.items():
            if k.startswith('CNI_'):
                setattr(self, k, v)
        if cfg is None:
            self.config = CNIConfig(env['config_zun'])
        else:
            self.config = cfg
        self.args = CNIArgs(self.CNI_ARGS)

    def __repr__(self):
        return repr({key: value for key, value in self.__dict__.items() if
                     key.startswith('CNI_')})
