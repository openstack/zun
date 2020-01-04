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


from kuryr.lib.binding.drivers import utils as kl_utils
from kuryr.lib import constants as kl_const
from os_vif.objects import fixed_ip as osv_fixed_ip
from os_vif.objects import network as osv_network
from os_vif.objects import route as osv_route
from os_vif.objects import subnet as osv_subnet
from os_vif.objects import vif as osv_vif
from oslo_config import cfg as oslo_cfg
from stevedore import driver as stv_driver

from zun.common import exception
from zun.common import utils


# REVISIT(ivc): consider making this module part of kuryr-lib
_VIF_TRANSLATOR_NAMESPACE = "zun.vif_translators"
_VIF_MANAGERS = {}


def _neutron_to_osvif_network(os_network):
    """Converts Neutron network to os-vif Subnet.

    :param os_network: openstack.network.v2.netwrork.Network object.
    :return: an os-vif Network object
    """

    obj = osv_network.Network(id=os_network['id'])

    if os_network['name'] is not None:
        obj.label = os_network['name']

    if os_network['mtu'] is not None:
        obj.mtu = os_network['mtu']

    # Vlan information will be used later in Sriov binding driver
    if os_network['provider:network_type'] == 'vlan':
        obj.should_provide_vlan = True
        obj.vlan = os_network['provider:segmentation_id']

    return obj


def _neutron_to_osvif_subnet(os_subnet):
    """Converts Neutron subnet to os-vif Subnet.

    :param os_subnet: openstack.network.v2.subnet.Subnet object
    :return: an os-vif Subnet object
    """

    obj = osv_subnet.Subnet(
        cidr=os_subnet['cidr'],
        dns=os_subnet['dns_nameservers'],
        routes=_neutron_to_osvif_routes(os_subnet['host_routes']))

    if os_subnet['gateway_ip'] is not None:
        obj.gateway = os_subnet['gateway_ip']

    return obj


def _neutron_to_osvif_routes(neutron_routes):
    """Converts Neutron host_routes to os-vif RouteList.

    :param neutron_routes: list of routes as returned by neutron client's
                           'show_subnet' in 'host_routes' attribute
    :return: an os-vif RouteList object
    """

    # NOTE(gryf): Nested attributes for OpenStackSDK objects are simple types,
    # like dicts and lists, that's why neutron_routes is a list of dicts.
    obj_list = [osv_route.Route(cidr=route['destination'],
                                gateway=route['nexthop'])
                for route in neutron_routes]

    return osv_route.RouteList(objects=obj_list)


def _make_vif_subnet(subnets, subnet_id):
    """Makes a copy of an os-vif Subnet from subnets mapping.

    :param subnets: subnet mapping
    :param subnet_id: ID of the subnet to extract from 'subnets' mapping
    :return: a copy of an os-vif Subnet object matching 'subnet_id'
    """
    subnet = subnets[subnet_id]

    vif_subnet = _neutron_to_osvif_subnet(subnet)
    vif_subnet.ips = osv_fixed_ip.FixedIPList(objects=[])
    return vif_subnet


def _make_vif_subnets(neutron_port, subnets):
    """Gets a list of os-vif Subnet objects for port.

    :param neutron_port: dict containing port information as returned by
                         neutron client's 'show_port'
    :param subnets: subnet mapping
    :return: list of os-vif Subnet object
    """

    vif_subnets = {}

    for neutron_fixed_ip in neutron_port.get('fixed_ips', []):
        subnet_id = neutron_fixed_ip['subnet_id']
        ip_address = neutron_fixed_ip['ip_address']

        if subnet_id not in subnets:
            continue

        try:
            subnet = vif_subnets[subnet_id]
        except KeyError:
            subnet = _make_vif_subnet(subnets, subnet_id)
            vif_subnets[subnet_id] = subnet

        subnet.ips.objects.append(osv_fixed_ip.FixedIP(address=ip_address))

    if not vif_subnets:
        raise exception.ZunException(
            "No valid subnets found for port %(port_id)s"
            % {'port_id': neutron_port.get('id')})

    return list(vif_subnets.values())


def _make_vif_network(neutron_port, network, subnets):
    """Get an os-vif Network object for port.

    :param neutron_port: dict containing port information as returned by
                         neutron client's 'show_port'
    :param subnets: subnet mapping
    :return: os-vif Network object
    """

    vif_network = _neutron_to_osvif_network(network)
    vif_network.subnets = osv_subnet.SubnetList(
        objects=_make_vif_subnets(neutron_port, subnets))

    return vif_network


def _get_vif_name(neutron_port):
    """Gets a VIF device name for port.

    :param neutron_port: dict containing port information as returned by
                         neutron client's 'show_port'
    """

    vif_name, _ = kl_utils.get_veth_pair_names(neutron_port['id'])
    return vif_name


def _get_ovs_hybrid_bridge_name(neutron_port):
    """Gets a name of the Linux bridge name for hybrid OpenVSwitch port.

    :param neutron_port: dict containing port information as returned by
                         neutron client's 'show_port'
    """
    return ('qbr' + neutron_port['id'])[:kl_const.NIC_NAME_LEN]


def neutron_to_osvif_vif_ovs(vif_plugin, neutron_port, network, subnets):
    """Converts Neutron port to VIF object for os-vif 'ovs' plugin.

    :param vif_plugin: name of the os-vif plugin to use (i.e. 'ovs')
    :param neutron_port: dict containing port information as returned by
                         neutron client's 'show_port'
    :param subnets: subnet mapping
    :return: os-vif VIF object
    """

    profile = osv_vif.VIFPortProfileOpenVSwitch(
        interface_id=neutron_port['id'])

    details = neutron_port.get('binding:vif_details', {})
    ovs_bridge = details.get('bridge_name',
                             oslo_cfg.CONF.neutron.ovs_bridge)
    if not ovs_bridge:
        raise oslo_cfg.RequiredOptError('ovs_bridge', 'neutron_defaults')

    network = _make_vif_network(neutron_port, network, subnets)
    network.bridge = ovs_bridge

    if details.get('ovs_hybrid_plug'):
        vif = osv_vif.VIFBridge(
            id=neutron_port['id'],
            address=neutron_port['mac_address'],
            network=network,
            has_traffic_filtering=details.get('port_filter', False),
            preserve_on_delete=False,
            active=utils.is_port_active(neutron_port),
            port_profile=profile,
            plugin=vif_plugin,
            vif_name=_get_vif_name(neutron_port),
            bridge_name=_get_ovs_hybrid_bridge_name(neutron_port))
    else:
        vif = osv_vif.VIFOpenVSwitch(
            id=neutron_port['id'],
            address=neutron_port['mac_address'],
            network=network,
            has_traffic_filtering=details.get('port_filter', False),
            preserve_on_delete=False,
            active=utils.is_port_active(neutron_port),
            port_profile=profile,
            plugin=vif_plugin,
            vif_name=_get_vif_name(neutron_port),
            bridge_name=network.bridge)

    return vif


def neutron_to_osvif_vif(vif_translator, neutron_port, network, subnets):
    """Converts Neutron port to os-vif VIF object.

    :param vif_translator: name of the traslator for the os-vif plugin to use
    :param neutron_port: dict containing port information as returned by
                         neutron client
    :param subnets: subnet mapping
    :return: os-vif VIF object
    """

    try:
        mgr = _VIF_MANAGERS[vif_translator]
    except KeyError:
        mgr = stv_driver.DriverManager(
            namespace=_VIF_TRANSLATOR_NAMESPACE,
            name=vif_translator, invoke_on_load=False)
        _VIF_MANAGERS[vif_translator] = mgr

    return mgr.driver(vif_translator, neutron_port, network, subnets)
