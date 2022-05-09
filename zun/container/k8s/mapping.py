from oslo_log import log as logging

from zun.common import utils
from zun.conf import CONF

LABEL_NAMESPACE = "zun.openstack.org"
LABELS = {
    "uuid": f"{LABEL_NAMESPACE}/uuid",
    "type": f"{LABEL_NAMESPACE}/type",
    "project_id": f"{LABEL_NAMESPACE}/project_id",
    "exposed": f"{LABEL_NAMESPACE}/exposed",
    "blazar_reservation_id": "blazar.openstack.org/reservation_id",
    "blazar_project_id": "blazar.openstack.org/project_id",
    "neutron_security_group": "neutron.openstack.org/security_group",
    "neutron_revision_number": "neutron.openstack.org/revision_number",
}

LOG = logging.getLogger(__name__)


def device_profile_resources():
    dp_mappings = CONF.k8s.device_profile_mappings
    if not dp_mappings:
        return None

    resources_by_device_profile = {}
    for mapping in dp_mappings:
        dp_name, k8s_resources = mapping.split("=")
        # Convert <dp_name>=<k8s_resource>:<amount>[,<k8s_resource>:<amount>...]
        # to {<dp_name>: {<k8s_resource>: <amount>[, <k8s_resource>: <amount>...]}
        dp_resources = resources_by_device_profile.setdefault(dp_name, {})
        for k8s_resource in k8s_resources.split(","):
            k8s_resource_name, k8s_resource_amount = k8s_resource.split(":")
            dp_resources[k8s_resource_name] = int(k8s_resource_amount)

    return resources_by_device_profile


def resources_request(container):
    if not container.annotations:
        return None

    device_profiles = container.annotations.get(utils.DEVICE_PROFILE_ANNOTATION)
    if not device_profiles:
        return None

    dp_resources = device_profile_resources()
    if not dp_resources:
        return None

    resources = {"limits": {}}
    for dp_name in device_profiles.split(","):
        if dp_name not in dp_resources:
            raise ValueError(
                "Missing mapping for device_profile '%s', ensure it has been added "
                "to device_profile_mappings." % dp_name)
        resources["limits"].update(dp_resources[dp_name])

    return resources


def pod_labels(container):
    labels = container.labels or {}
    labels[LABELS["type"]] = "container"
    labels[LABELS["uuid"]] = container.uuid
    labels[LABELS["project_id"]] = container.project_id
    labels[LABELS["exposed"]] = "true" if container.exposed_ports else "false"
    return labels


def container_env(container):
    if not container.environment:
        return []
    return [
        {"name": name, "value": value}
        for name, value in container.environment.items()
    ]


def container_ports(container):
    ports = []
    for port in (container.exposed_ports or []):
        port_spec = port.split("/")
        portnum = int(port_spec[0])
        if len(port_spec) > 1:
            protocol = port_spec[1].upper()
            # Should have been asserted in API layer, just double-check.
            assert protocol in ["TCP", "UDP"]
        else:
            protocol = "TCP"
        ports.append({"port": portnum, "protocol": protocol})
    return ports


def label_selector(container):
    return f"{LABELS['uuid']}={container.uuid}"


def name(container):
    return "zun-" + container.uuid


def namespace(container):
    return {
        "metadata": {
            "name": container.project_id,
            "labels": {
                LABELS["project_id"]: container.project_id,
            },
        }
    }


def deployment(container, image, requested_volumes=None, image_pull_secrets=None):
    resources = resources_request(container)
    labels = pod_labels(container)
    env = container_env(container)
    liveness_probe = restart_policy = None

    if image['tag']:
        image_repo = image['repo'] + ":" + image['tag']
    else:
        image_repo = image['repo']

    if container.restart_policy:
        restart_policy_map = {
            "no": "Never",
            "always": "Always",
            "on-failure": "OnFailure",
            # No direct mapping for this in k8s
            "unless-stopped": "OnFailure",
        }
        restart_policy = restart_policy_map.get(container.restart_policy["Name"])

    # The time unit in docker of heath checking is us, and the unit
    # of interval and timeout is seconds.
    if container.healthcheck:
        liveness_probe = {
            "exec": container.healthcheck.get("test", ""),
            "failureThreshold": int(container.healthcheck.get('retries', 3)),
            "periodSeconds": int(container.healthcheck.get("interval", 10)),
            "timeoutSeconds": int(container.healthcheck.get('timeout', 0)),
        }

    deployment_labels = {
        LABELS["uuid"]: container.uuid,
        LABELS["project_id"]: container.project_id,
    }

    # Ensure user pods are never scheduled onto control plane infra
    node_selector_expressions = [
        {
            "key": "node-role.kubernetes.io/control-plane",
            "operator": "NotIn",
            "values": ["true"]
        },
    ]

    reservation_id = container.annotations.get(utils.RESERVATION_ANNOTATION)
    if reservation_id:
        # Add the reservation ID to the deployment labels; this enables the reservation
        # system to find the deployments tied to the reservation for cleanup.
        deployment_labels[LABELS["blazar_reservation_id"]] = reservation_id
        # Ensure the deployment lands on a reserved kubelet.
        node_selector_expressions.extend([
            {
                "key": LABELS["blazar_project_id"],
                "operator": "In",
                "values": [container.project_id],
            },
            {
                "key": LABELS["blazar_reservation_id"],
                "operator": "In",
                "values": [reservation_id],
            }
        ])

    volumes = []
    volume_mounts = []
    if requested_volumes:
        for volmap in requested_volumes.get(container.uuid, []):
            # TODO: need to detect what the volume provider is and not use configmap
            # in the 'volumes' configuration, instead use PersistentVolume claim.
            vol_name = config_map_name(volmap)
            volume_mounts.append({
                "name": vol_name,
                "subPath": "file",  # We always store 1 binaryData key and it is 'file'
                "mountPath": volmap.container_path,
            })
            volumes.append({
                "name": vol_name,
                "configMap": {"name": vol_name},
            })

    secrets_spec = []
    if image_pull_secrets:
        secrets_spec = [{"name": name} for name in image_pull_secrets]

    return {
        "metadata": {
            "name": name(container),
            "labels": deployment_labels,
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": labels,
            },
            "template": {
                "metadata": {
                    "labels": labels,
                },
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [
                                    {
                                        "matchExpressions": node_selector_expressions,
                                    },
                                ],
                            },
                        },
                    },
                    "containers": [
                        {
                            "args": container.command,
                            # NOTE(jason): update in Xena when entrypoint exists.
                            "command": getattr(container, "entrypoint", None),
                            "env": env,
                            "image": image_repo,
                            "imagePullPolicy": "",
                            "name": container.name,
                            "ports": [
                                {
                                    "containerPort": port_spec["port"],
                                    "protocol": port_spec["protocol"]
                                } for port_spec in container_ports(container)
                            ],
                            "stdin": container.interactive,
                            "tty": container.tty,
                            "volumeDevices": [],
                            "volumeMounts": volume_mounts,
                            "workingDir": container.workdir,
                            "resources": resources,
                            "livenessProbe": liveness_probe,
                        }
                    ],
                    "hostname": container.hostname,
                    "nodeName": None, # Could be a specific node
                    "volumes": volumes,
                    "restartPolicy": restart_policy,
                    "privileged": container.privileged,
                    "imagePullSecrets": secrets_spec,
                }
            },
        },
    }


def default_network_policy(project_id):
    return {
        "metadata": {
            "name": "default",
        },
        "spec": {
            # Only allow ingress from pods in same namespace
            "ingress": [{
                "from": [{
                    "namespaceSelector": {
                        "matchLabels": {
                            LABELS["project_id"]: project_id,
                        },
                    }
                }],
            }],
            # Allow all egress
            "egress": [{}],
            "policyTypes": ["Ingress", "Egress"],
        },
    }


def exposed_port_network_policy(container):
    return {
        "metadata": {
            "name": f"expose-{container.uuid}",
            "labels": {
                LABELS["uuid"]: container.uuid,
            },
        },
        "spec": {
            "podSelector": {
                "matchLabels": {
                    LABELS["uuid"]: container.uuid,
                },
            },
            "ingress": [
                {
                    # Allow from all IPs
                    "ports": [
                        {
                            "port": port_spec["port"],
                            "protocol": port_spec["protocol"]
                        } for port_spec in container_ports(container)
                    ],
                },
            ],
        },
    }


def security_group_network_policy(security_group, container_uuids=None):
    if container_uuids is None:
        container_uuids = []

    ingress, egress, policy_types = [], [], []

    policy_spec = {
        "podSelector": {
            "matchExpressions": [{
                "key": LABELS["uuid"],
                "operator": "In",
                "values": container_uuids,
            }]
        },
        "policyTypes": policy_types,
    }

    for rule in security_group["security_group_rules"]:
        peer = {}
        if rule["remote_ip_prefix"]:
            peer["ipBlock"] = {"cidr": rule["remote_ip_prefix"]}
        if rule["remote_group_id"]:
            LOG.warning((
                "Remote groups are currently not supported for security groups "
                "in K8s"
            ))

        port = {"protocol": (rule["protocol"] or "tcp").upper()}
        min_port, max_port = rule["port_range_min"], rule["port_range_max"]
        if min_port:
            port["port"] = min_port
        if max_port and min_port != max_port:
            port["endPort"] = max_port

        if rule["direction"] == "ingress":
            ingress_rule = {"ports": [port]}
            if peer:
                ingress_rule["from"] = [peer]
            ingress.append(ingress_rule)
        elif rule["direction"] == "egress":
            egress_rule = {"ports": [port]}
            if peer:
                egress_rule["to"] = [peer]
            egress.append(egress_rule)
        else:
            LOG.error("Unknown security group direction %s", rule["direction"])

    if ingress:
        policy_spec["ingress"] = ingress
        policy_types.append("Ingress")
    if egress:
        policy_spec["egress"] = egress
        policy_types.append("Egress")

    return {
        "metadata": {
            "name": f"sg-{security_group['id']}",
            "labels": {
                LABELS["neutron_security_group"]: security_group["id"],
                LABELS["neutron_revision_number"]: str(security_group["revision_number"]),
            }
        },
        "spec": policy_spec,
    }


def config_map_name(volmap):
    # A shorthand for just getting the name of the volume mapping w/o having to also
    # decode the file contents.
    return f"zun-{volmap.volume.uuid}"


def config_map(volmap):
    return {
        "metadata": {
            "name": config_map_name(volmap)
        },
        "binaryData": {
            "file": volmap.contents,
        },
    }
