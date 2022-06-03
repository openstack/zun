import contextlib
import typing

from kubernetes.client import V1LabelSelectorRequirement
from neutronclient.common import exceptions as neutron_exc
from oslo_log import log as logging
from oslo_utils import excutils

from zun.common import exception
from zun.conf import CONF
from zun.container.k8s import mapping
from zun.network import network, neutron

if typing.TYPE_CHECKING:
    from kubernetes.client import NetworkingV1Api, V1LabelSelector

BINDING_PROFILE = "binding:profile"
BINDING_HOST_ID = "binding:host_id"
DEVICE_OWNER = "k8s:cni"
UNDEFINED_NETWORK = "no_network"

LOG = logging.getLogger(__name__)


class K8sNetwork(network.Network):
    def init(self, context, k8s_net_api: "NetworkingV1Api"):
        # self.docker = docker_api
        self.neutron_api = neutron.NeutronAPI(context)
        self.k8s_net_api = k8s_net_api
        self.context = context

        if CONF.k8s.neutron_network:
            self.neutron_network_id = (
                self.neutron_api.get_neutron_network(CONF.k8s.neutron_network)["id"])
        else:
            self.neutron_network_id = UNDEFINED_NETWORK

    def create_network(self, network_name, neutron_net_id):
        raise NotImplementedError("Cannot create new networks in K8s")

    def remove_network(self, network_name):
        raise NotImplementedError("Cannot remove networks managed by K8s")

    def inspect_network(self, network_name):
        raise NotImplementedError("Cannot inspect networks managed by K8s")

    def list_networks(self, **kwargs):
        return []

    def connect_container_to_network(self, container, network_name,
                                     requested_fixed_ips):
        """Plug a port in Neutron for the K8s container/pod.

        This is a bit of an opposite operation as to how other network drivers work.
        Instead of creating a port, then wiring it in the container engine/network,
        then marking the port as bound, we are instead just mapping K8s network state
        into Neutron (i.e., there is no step to "wire" the connection to K8s, as it
        has already been done by this point.)
        """
        network_addrs = container.addresses.get(self.neutron_network_id, [])
        # Extract the current list of container addresses and associated ports.
        # We keep a single port for each container and adjust its addresses if they
        # change on the pod. This prevents disruptions to floating IP bindings.
        container_ips = set(addr["addr"] for addr in network_addrs)

        if set(requested_fixed_ips) == container_ips:
            # As an optimization, we assume there is nothing to process in this case.
            return container.addresses

        security_groups = container.security_groups or []
        for sec_group in security_groups:
            self._apply_network_policy(container, sec_group)

        # FIXME(jason): this currently assumes that each container is associated with
        # only one port, which can have multiple fixed_ips. This may not be what we
        # want long-term, but it's sufficient for now.
        all_ports = self._get_ports_for_addrs(network_addrs)
        port_id = all_ports[0] if all_ports else None
        port_dict = {
            "device_id": container.uuid,
            "device_owner": DEVICE_OWNER,
            BINDING_HOST_ID: container.host,
            "fixed_ips": [{"ip_address": ip} for ip in requested_fixed_ips],
            "security_groups": security_groups,
        }

        if port_id:
            try:
                self.neutron_api.update_port(port_id, {"port": port_dict}, admin=True)
                LOG.info(
                    f"Updated port {port_id} IP assignments for "
                    f"{container.uuid}")
            except neutron_exc.PortNotFoundClient:
                LOG.info(
                    f"Port {port_id} was deleted, will re-create with IP assignments "
                    f"for {container.uuid}"
                )
                port_id = None

        if not port_id and self.neutron_network_id != UNDEFINED_NETWORK:
            # Only create ports if we have defined a neutron network they can go on.
            port_dict.update({
                "name": mapping.name(container),
                "network_id": self.neutron_network_id,
                "tenant_id": container.project_id
            })

            try:
                port = self.neutron_api.create_port({"port": port_dict}, admin=True)["port"]
            except neutron_exc.IpAddressAlreadyAllocatedClient:
                # This pod has the IP, so we can safely delete the existing port.
                # After deletion, we'll wait for the next sync process to clean up
                # by returning from the function early.
                existing_ports = self.neutron_api.list_ports(
                    fixed_ips=[f"ip_address={ip}" for ip in requested_fixed_ips])["ports"]
                # Safeguard, prevent from deleting too many in case listing returns
                # too many!
                assert len(existing_ports) <= len(requested_fixed_ips)
                for existing_port in existing_ports:
                    self.neutron_api.delete_port(existing_port["id"])
                    LOG.info("Deleting conflicting port %s", existing_port["id"])
                return {}

            port_id = port["id"]
            LOG.info(f"Created port {port_id} for {container.uuid}")

        return {
            self.neutron_network_id: [
                {
                    'addr': ip,
                    'version': 4,
                    'port': port_id
                } for ip in requested_fixed_ips
            ]
        }

    def disconnect_container_from_network(self, container, network_name):
        addrs_list = []
        if container.addresses:
            addrs_list = container.addresses.get(self.neutron_network_id, [])

        for port_id in self._get_ports_for_addrs(addrs_list):
            try:
                self.neutron_api.delete_port(port_id)
            except neutron_exc.PortNotFoundClient:
                LOG.warning("Port %s has already been deleted", port_id)

    def _apply_network_policy(self, container, security_group_id):
        security_group = self._get_security_group(security_group_id)

        with self._adjust_policy_match_expressions(container, security_group) as match_expressions:
            if match_expressions is not None:
                for expr in match_expressions:
                    if expr.key == mapping.LABELS["uuid"] and expr.operator == "In":
                        if container.uuid not in expr.values:
                            expr.values.append(container.uuid)
                        # FIXME(jason): fixes up old security groups w/ dupes but
                        # shouldn't be necessary long term.
                        expr.values = list(set(expr.values))
                        break
                else:
                    match_expressions.append(V1LabelSelectorRequirement(
                        key=mapping.LABELS["uuid"],
                        operator="In",
                        values=[container.uuid],
                    ))
            else:
                # No existing network policy
                self.k8s_net_api.create_namespaced_network_policy(container.project_id,
                    mapping.security_group_network_policy(
                        security_group, [container.uuid]))
                LOG.info(
                    f"Created network policy for security group {security_group_id}")

    def _unapply_network_policy(self, container, security_group_id):
        security_group = self._get_security_group(security_group_id)

        with self._adjust_policy_match_expressions(container, security_group) as match_expressions:
            if match_expressions is not None:
                for expr in match_expressions:
                    if expr.key == mapping.LABELS["uuid"] and expr.operator == "In":
                        expr.values.remove(container.uuid)
                        break

    def _get_security_group(self, security_group_id):
        return self.neutron_api.show_security_group(security_group_id)["security_group"]

    @contextlib.contextmanager
    def _adjust_policy_match_expressions(self, container, security_group):
        """Provide a hook for updating pod match expressions for a sg's networkpolicy.

        This context manager will yield the list of matchExpressions for the
        security group's networkpolicy, if one exists. If there is no such policy, it
        will yield None. The list of match expressions can be adjusted inside the
        context manager. When the manager exits, it will apply the changes to the
        networkpolicy in K8s.
        """
        sg_id = security_group["id"]
        policy_list = self.k8s_net_api.list_namespaced_network_policy(
            container.project_id,
            label_selector=f"{mapping.LABELS['neutron_security_group']}={sg_id}"
        )
        network_policy = policy_list.items[0] if policy_list.items else None

        if network_policy:
            pod_selector: "V1LabelSelector" = network_policy.spec.pod_selector
            match_expressions: "list[V1LabelSelectorRequirement]" = (
                pod_selector.match_expressions or [])

            yield match_expressions

            match_labels = pod_selector.match_labels
            expected_policy = mapping.security_group_network_policy(security_group)
            expected_spec = expected_policy["spec"]
            expected_spec["podSelector"] = {
                "matchExpressions": [req.to_dict() for req in match_expressions],
                # Ensure we preserve matchLabels, if they were set
                "matchLabels": match_labels.to_dict() if match_labels else None,
            }
            name = expected_policy["metadata"]["name"]
            self.k8s_net_api.patch_namespaced_network_policy(
                name,
                container.project_id, {
                    "spec": expected_spec,
                })
            LOG.info(f"Patched network policy {name} for security group {sg_id}")
        else:
            yield

    def _get_ports_for_addrs(self, addrs_list):
        """For a list of container addresses, find the port IDs."""
        port_ids = set()
        for addr in addrs_list:
            if addr.get("port"):
                port_ids.add(addr["port"])
        return list(port_ids)

    def add_security_groups_to_ports(self, container, security_group_ids):
        for sg_id in security_group_ids:
            self._apply_network_policy(container, sg_id)

        for port in self._container_ports(container):
            new_groups = set(port.get("security_groups", [])) + set(security_group_ids)
            updated_port = {'security_groups': list(new_groups)}
            try:
                LOG.info("Adding security groups %(security_group_ids)s "
                         "to port %(port_id)s",
                         {'security_group_ids': security_group_ids,
                          'port_id': port['id']})
                self.neutron_api.update_port(port['id'],
                                             {'port': updated_port},
                                             admin=True)
            except neutron_exc.NeutronClientException as e:
                if e.status_code == 400:
                    raise exception.SecurityGroupCannotBeApplied(e)
                else:
                    raise
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Neutron Error:")

    def remove_security_groups_from_ports(self, container, security_group_ids):
        for sg_id in security_group_ids:
            self._unapply_network_policy(container, sg_id)

        for port in self._container_ports(container):
            new_groups = set(port["security_groups"]) - set(security_group_ids)
            updated_port = {'security_groups': list(new_groups)}
            try:
                LOG.info("Removing security groups %(security_group_ids)s "
                         "from port %(port_id)s",
                         {'security_group_ids': security_group_ids,
                          'port_id': port['id']})
                self.neutron_api.update_port(port['id'],
                                             {'port': updated_port},
                                             admin=True)
            except neutron_exc.NeutronClientException as e:
                if e.status_code == 400:
                    raise exception.SecurityGroupCannotBeRemoved(e)
                else:
                    raise
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Neutron Error:")

    def _container_ports(self, container):
        port_ids = set()
        for network_id in container.addresses:
            port_ids += self._get_ports_for_addrs(container.addresses[network_id])

        neutron_ports = self.neutron_api.list_ports(
            tenant_id=container.project_id).get('ports', [])
        return [p for p in neutron_ports if p['id'] in port_ids]
