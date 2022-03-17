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
}


def resources_request(container):
    if not container.annotations:
        return None

    device_profiles = container.annotations.get(utils.DEVICE_PROFILE_ANNOTATION)
    if not device_profiles:
        return None

    dp_mappings = CONF.k8s.device_profile_mappings
    if not dp_mappings:
        return None

    resource_map = {}
    for mapping in dp_mappings:
        dp_name, k8s_resources = mapping.split("=")
        # Convert <dp_name>=<k8s_resource>:<amount>[,<k8s_resource>:<amount>...]
        # to {<dp_name>: {<k8s_resource>: <amount>[, <k8s_resource>: <amount>...]}
        dp_resources = resource_map.setdefault(dp_name, {})
        for k8s_resource in k8s_resources.split(","):
            k8s_resource_name, k8s_resource_amount = k8s_resource.split(":")
            dp_resources[k8s_resource_name] = int(k8s_resource_amount)

    resources_request = {"limits": {}}
    for dp_name in device_profiles.split(","):
        if dp_name not in resource_map:
            raise ValueError(
                "Missing mapping for device_profile '%s', ensure it has been added "
                "to device_profile_mappings." % dp_name)
        resources_request["limits"].update(resource_map[dp_name])

    return resources_request


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
    container_ports = []
    for port in (container.exposed_ports or []):
        port_spec = port.split("/")
        portnum = int(port_spec[0])
        if len(port_spec) > 1:
            protocol = port_spec[1].upper()
            # Should have been asserted in API layer, just double-check.
            assert protocol in ["TCP", "UDP"]
        else:
            protocol = "TCP"
        container_ports.append({"port": portnum, "protocol": protocol})
    return container_ports


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


def deployment(container, image):
    resources_request = resources_request(container)
    pod_labels = pod_labels(container)
    container_env = container_env(container)
    liveness_probe = restart_policy = None

    if image['tag']:
        image_repo = image['repo'] + ":" + image['tag']
    else:
        image_repo = image['repo']

    if container.restart_policy:
        restart_policy = container.restart_policy["Name"]

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

    return {
        "metadata": {
            "name": name(container),
            "labels": deployment_labels,
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": pod_labels,
            },
            "template": {
                "metadata": {
                    "labels": pod_labels,
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
                            "env": container_env,
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
                            "volumeMounts": [],
                            "workingDir": container.workdir,
                            "resources": resources_request,
                            "livenessProbe": liveness_probe,
                        }
                    ],
                    "hostname": container.hostname,
                    "nodeName": None, # Could be a specific node
                    "volumes": [],
                    "restartPolicy": restart_policy,
                    "privileged": container.privileged,
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
